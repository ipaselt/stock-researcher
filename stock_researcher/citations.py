"""The hallucination guard: every number an agent states must be in data/<T>.json or data/<T>.score.json.

Hard checks per agent file data/<T>/<agent>.md (exactly one ```json block allowed):
- the json block parses, carries dimension/grade/confidence/numbers_cited, and every cited {key, value}
  resolves by dotted path in the snapshot or the score JSON with a matching value;
- the prose, and the block's `reason` and `flags` strings (they are published too), are split into sentences.
  A citation is a parenthesised key list, `(valuation.forward_pe)` or `(a.b, c.d)` (backticks allowed; a
  single-segment key such as `total` counts when it exists), or a key with its value, `(growth.revenue_cagr_3y
  1.8%)`, `(key: 1.8%)`, `(technical.golden_cross = true)`. Every dotted key must exist. Every number between
  the previous citation (or the sentence start) and a citation must match one of that citation's keys; a
  decimal or unit-bearing number after the sentence's last citation, or in a sentence with no citation, is
  uncited and fails. Plain integers outside a citation window are ignored, and so are dates, fiscal years,
  `N-day`-style compounds, ranges like `1-5`, `S&P 500`, list numerals, `RSI(14)`, and numbers glued to letters.
- Units: % = /100; B/bn/billion, M/mn/million, T/tn/trillion scale; x/X/times and $ as-is; bps and pp fail.

Numbers match within 1% relative (absolute 1e-9 when the reference is 0). In prose a number also matches when
it is the reference rounded to the decimals it is printed with (at least one decimal, the agent contract's
rounding limit): 2.2% for 0.0217 is honest rounding, 2% for 0.0249 is not. A list reference matches a number
equal to any element.
"""
import json
import re
from pathlib import Path

SKIP_FILES = {"skeleton.md", "verdict.md"}
REQUIRED_KEYS = ("dimension", "grade", "confidence", "numbers_cited")
REL_TOL, ABS_TOL = 0.01, 1e-9
UNIT_FACTORS = {"%": 0.01, "x": 1.0, "X": 1.0, "times": 1.0, "": 1.0,
                "B": 1e9, "bn": 1e9, "billion": 1e9, "M": 1e6, "mn": 1e6, "million": 1e6,
                "T": 1e12, "tn": 1e12, "trillion": 1e12}
UNSUPPORTED_UNITS = {"bps", "pp"}

JSON_BLOCK_RE = re.compile(r"```json[ \t]*\n(.*?)\n[ \t]*```", re.DOTALL)
KEY_TOKEN_RE = re.compile(r"[a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*)*")
UNIT = r"%|times|billion|bn|million|mn|trillion|tn|bps|pp|x|X|B|M|T"
# sign, $, sign, digits (1,234 thousands allowed), decimals, unit: five groups.
NUMBER = (rf"([-+−]?)(\$?)([-−]?)((?:\d{{1,3}}(?:,\d{{3}})+|\d+)(?:\.\d+)?)(?:\s?({UNIT})(?![\w]))?")
# ... in running text: not the tail of a word, decimal, range, ratio or time.
NUMBER_RE = re.compile(rf"(?<![\w.\-−/:&]){NUMBER}")
# A key with its value inside the parentheses: groups 1 key, 2-6 number, 7 true/false/null.
INLINE_RE = re.compile(rf"^({KEY_TOKEN_RE.pattern})(?:\s*[:=]\s*|\s+)(?:{NUMBER}|(true|false|null))$")
PAREN_RE = re.compile(r"\(([^()]*)\)")
NOISE_RE = re.compile(r"https?://[^\s)\]]+|\b\d{4}-\d{2}-\d{2}\b|S&P\s?500|`|\*|(?<![A-Za-z0-9])_|_(?![A-Za-z0-9])"
                      r"|^[ \t]*(?:[-+]|\d+[.)])[ \t]+", re.MULTILINE)
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+|;|\n")
MISSING = object()


def resolve(key: str, sources: dict[str, dict]):
    """(source name, value) for the dotted key in the first source that has it, else (None, MISSING)."""
    for name, data in sources.items():
        node = data
        for part in key.split("."):
            if not isinstance(node, dict) or part not in node:
                break
            node = node[part]
        else:
            return name, node
    return None, MISSING


def _num_match(cited: float, ref: float) -> bool:
    if ref == 0:
        return abs(cited) <= ABS_TOL
    return abs(cited - ref) <= REL_TOL * abs(ref)


def _is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def values_match(cited, ref) -> bool:
    """The JSON-block rule: numbers within 1%, null <-> None, bools/strings exact, lists element-wise;
    a scalar cited for a list reference matches when it equals any element."""
    if ref is None or cited is None:
        return ref is None and cited is None
    if isinstance(ref, list) and not isinstance(cited, list):
        return any(values_match(cited, r) for r in ref)
    if isinstance(ref, bool) or isinstance(cited, bool):
        return type(ref) is type(cited) and ref == cited
    if _is_num(ref) and _is_num(cited):
        return _num_match(cited, ref)
    if isinstance(ref, list) and isinstance(cited, list):
        return len(ref) == len(cited) and all(values_match(c, r) for c, r in zip(cited, ref))
    return type(ref) is type(cited) and ref == cited


def _show(v) -> str:
    if isinstance(v, float):
        return f"{v:.4g}"
    if isinstance(v, list):
        return "[" + ", ".join(_show(x) for x in v) + "]"
    return json.dumps(v)


def _prose_match(digits: str, negative: bool, displayed: float) -> bool:
    """A printed number vs the reference in the same display units: 1% relative, or honest rounding."""
    cited = -float(digits) if negative else float(digits)
    decimals = len(digits.split(".")[1]) if "." in digits else 0
    return _num_match(cited, displayed) or abs(cited - displayed) <= 0.5 * 10 ** -max(decimals, 1) + ABS_TOL


class _Number:
    """A printed number: `groups` are NUMBER_RE's five (sign, $, sign, digits, unit)."""

    def __init__(self, groups):
        sign, dollar, inner_sign, digits, unit = groups
        self.negative = any(c in sign + inner_sign for c in "-−")
        self.digits, self.unit, self.dollar = digits.replace(",", ""), unit or "", bool(dollar)
        self.shown = f"{'-' if self.negative else ''}{'$' if dollar else ''}{digits}{self.unit}"

    @property
    def counts_when_uncited(self) -> bool:
        return "." in self.digits or bool(self.unit) or self.dollar

    def failure(self, found: dict[str, tuple]) -> str | None:
        """None when the number fits one of the cited keys, else why not."""
        if self.unit in UNSUPPORTED_UNITS:
            return f"unsupported unit in {self.shown} (restate as % or x)"
        factor = UNIT_FACTORS[self.unit]
        why = []
        for key, (where, ref) in found.items():
            if ref is None:
                why.append((key, "a null field", where))
                continue
            nums = [r for r in (ref if isinstance(ref, list) else [ref]) if _is_num(r)]
            if any(_prose_match(self.digits, self.negative, r / factor) for r in nums):
                return None
            shown_ref = ", ".join(f"{r / factor:.4g}{self.unit}" for r in nums) if nums else _show(ref)
            why.append((key, shown_ref, where))
        if len(why) == 1:
            key, shown_ref, where = why[0]
            if shown_ref == "a null field":
                return f"{key} cited {self.shown} for a null field (cited a value for a null field)"
            return f"{key} cited {self.shown} vs {shown_ref} in {where}"
        return f"{self.shown} matches none of " + "; ".join(f"{k} ({r})" for k, r, _ in why)


PERIOD_WORD_RE = re.compile(r"\s+(?:day|week|month|quarter|year)s?\b")
NAME_BEFORE_RE = re.compile(r"\b\w*[A-Z]\w*\s$")


def _skip(text: str, m: re.Match) -> bool:
    """Numbers that are not claims. Any number glued to letters (1y, 14th) or written as RSI(14); and, for plain
    integers (no unit, no $, no decimal): N-day compounds and ranges (3-year, 1-5, 3- or 5-year), periods
    (1 year, 3 months), fiscal years (19xx/20xx), and model numbers after a capitalised word (iPhone 18)."""
    after = text[m.end():m.end() + 2]
    if not m.group(5) and after[:1] and (after[0].isalnum() or after[0] == "_"):
        return True
    if m.start() >= 2 and text[m.start() - 1] == "(" and text[m.start() - 2].isalpha() and after[:1] == ")":
        return True
    if m.group(5) or m.group(2) or "." in m.group(4) or m.group(1) or m.group(3):
        return False
    digits = m.group(4)
    return (after[:1] == "-" or bool(PERIOD_WORD_RE.match(text, m.end()))
            or (len(digits) == 4 and digits[:2] in ("19", "20"))
            or bool(NAME_BEFORE_RE.search(text[max(0, m.start() - 30):m.start()])))


def _citation(content: str, sources: dict[str, dict]):
    """(keys, inline value match or None) when a parenthesis content is a citation, else None."""
    content = content.strip()
    inline = INLINE_RE.match(content)
    if inline and ("." in inline.group(1) or resolve(inline.group(1), sources)[1] is not MISSING):
        return [inline.group(1)], inline
    keys = [k.strip() for k in content.split(",")]
    if not keys or not all(KEY_TOKEN_RE.fullmatch(k) for k in keys):
        return None
    if not all("." in k or resolve(k, sources)[1] is not MISSING for k in keys):
        return None  # a plain word in parentheses, not a key
    return keys, None


def _excerpt(sentence: str) -> str:
    s = " ".join(sentence.split())
    return s if len(s) <= 80 else s[:77] + "..."


def check_prose(agent: str, text: str, sources: dict[str, dict]) -> list[str]:
    prose = NOISE_RE.sub(" ", JSON_BLOCK_RE.sub("", text))
    failures = []
    for sentence in SENTENCE_RE.split(prose):
        cites = []  # (start, end, found)
        for m in PAREN_RE.finditer(sentence):
            parsed = _citation(m.group(1), sources)
            if parsed is None:
                continue
            keys, inline = parsed
            found = {}
            for key in keys:
                where, ref = resolve(key, sources)
                if ref is MISSING:
                    failures.append(f"{agent}: prose cites unknown key ({key})")
                else:
                    found[key] = (where, ref)
            if inline and found:
                if inline.group(7) is not None:
                    key = keys[0]
                    if not values_match(json.loads(inline.group(7)), found[key][1]):
                        failures.append(f"{agent}: {key} cited {inline.group(7)} vs {_show(found[key][1])} "
                                        f"in {found[key][0]}")
                elif why := _Number(inline.groups()[1:6]).failure(found):
                    failures.append(f"{agent}: {why}")
            cites.append((m.start(), m.end(), found))
        for m in NUMBER_RE.finditer(sentence):
            if any(s <= m.start() < e for s, e, _ in cites) or _skip(sentence, m):
                continue
            number = _Number(m.groups())
            nxt = next((found for s, _, found in cites if s >= m.end()), None)
            if nxt is None:
                if number.counts_when_uncited:
                    failures.append(f'{agent}: uncited number {number.shown} in: "{_excerpt(sentence)}"')
            elif nxt and (why := number.failure(nxt)):
                failures.append(f"{agent}: {why}")
    return failures


def check_json_block(agent: str, text: str, sources: dict[str, dict]) -> list[str]:
    blocks = JSON_BLOCK_RE.findall(text)
    if not blocks:
        return [f"{agent}: no ```json block found"]
    if len(blocks) > 1:
        return [f"{agent}: {len(blocks)} ```json blocks found; exactly one allowed"]
    try:
        block = json.loads(blocks[0])
    except ValueError as err:
        return [f"{agent}: json block does not parse: {err}"]
    if not isinstance(block, dict):
        return [f"{agent}: json block is not an object"]
    missing = [k for k in REQUIRED_KEYS if k not in block]
    if missing:
        return [f"{agent}: json block missing {', '.join(missing)}"]
    cited = block["numbers_cited"]
    if not isinstance(cited, list):
        return [f"{agent}: numbers_cited is not a list"]
    failures = []
    for item in cited:
        if not isinstance(item, dict) or not isinstance(item.get("key"), str) or "value" not in item:
            failures.append(f"{agent}: numbers_cited entry {json.dumps(item)} is not {{key, value}}")
            continue
        key, value = item["key"], item["value"]
        where, ref = resolve(key, sources)
        if ref is MISSING:
            failures.append(f"{agent}: {key} not found in snapshot or score")
        elif not values_match(value, ref):
            failures.append(f"{agent}: {key} cited {_show(value)} vs {_show(ref)} in {where}")
    published = [block.get("reason")] + (block.get("flags") if isinstance(block.get("flags"), list) else [])
    for string in published:  # reason and flags are printed in the report: same rules as the prose
        if isinstance(string, str):
            failures += check_prose(agent, string, sources)
    return failures


def check_file(path: Path, sources: dict[str, dict]) -> list[str] | None:
    """Failure lines for one agent file ([] = PASS), or None for an empty file (the agent did not report)."""
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return None
    agent = path.stem
    return check_json_block(agent, text, sources) + check_prose(agent, text, sources)


def verify(ticker: str, data_dir: Path) -> dict[str, dict]:
    """{agent: {"status", "failures"}} for every non-empty agent file; writes data/<T>/citations.json unless empty.

    Raises FileNotFoundError when the snapshot or score JSON is missing, ValueError when one is not JSON.
    """
    data_dir = Path(data_dir)
    sources = {}
    for name, file in (("snapshot", f"{ticker}.json"), ("score", f"{ticker}.score.json")):
        path = data_dir / file
        if not path.exists():
            raise FileNotFoundError(f"missing {name}: {path.as_posix()}")
        sources[name] = json.loads(path.read_text(encoding="utf-8"))
    run_dir = data_dir / ticker
    results = {}
    for path in sorted(run_dir.glob("*.md")):
        if path.name in SKIP_FILES:
            continue
        failures = check_file(path, sources)
        if failures is not None:
            results[path.stem] = {"status": "FAIL" if failures else "PASS", "failures": failures}
    if results:
        (run_dir / "citations.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results
