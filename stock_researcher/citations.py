"""The hallucination guard: every number an agent states must be in data/<T>.json or data/<T>.score.json.

Two hard checks per agent file data/<T>/<agent>.md:
- the last ```json block parses, carries dimension/grade/confidence/numbers_cited, and every cited
  {key, value} resolves by dotted path in the snapshot or the score JSON with a matching value;
- every parenthesised dotted key in the prose, e.g. `28.1x (valuation.forward_pe)`, resolves, and a number
  written immediately before it (or inside the parentheses after the key: `(growth.revenue_cagr_3y 1.8%)`)
  matches the referenced value after unit normalisation: % = /100, B/M/T = x1e9/1e6/1e12, x and $ as-is.
  With several keys in one pair of parentheses the number must match one of them; a number next to a text,
  date or boolean field is not a claim about it. Other mentions (keys with extra words) are not checked.

Numbers match within 1% relative (absolute 1e-9 when the reference is 0). In prose a number also matches when
it is the reference rounded to the decimals it is printed with (at least one decimal, the agent contract's
rounding limit): 2.2% for 0.0217 is honest rounding, 2% for 0.0249 is not.
"""
import json
import re
from pathlib import Path

SKIP_FILES = {"skeleton.md", "verdict.md"}
REQUIRED_KEYS = ("dimension", "grade", "confidence", "numbers_cited")
REL_TOL, ABS_TOL = 0.01, 1e-9
UNIT_FACTORS = {"%": 0.01, "B": 1e9, "M": 1e6, "T": 1e12, "x": 1.0, "": 1.0}

JSON_BLOCK_RE = re.compile(r"```json[ \t]*\n(.*?)\n[ \t]*```", re.DOTALL)
KEY = r"[a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*)+"
CITATION_RE = re.compile(rf"\(\s*({KEY}(?:\s*,\s*{KEY})*)\s*\)")
# A number: sign, $, thousands commas, decimals, optional unit.
NUMBER = r"([-+−]?)\$?([-−]?)(\d[\d,]*(?:\.\d+)?)\s*(%|x|B|M|T)?"
# ... ending right before a citation's "(", and not the tail of a date or ratio (2026-10-29, 10/29, 10:30).
NUMBER_BEFORE_RE = re.compile(rf"(?<![\w.\-−/:]){NUMBER}\s*$")
# The value written inside the parentheses instead: (growth.revenue_cagr_3y 1.8%), (technical.golden_cross = true).
INLINE_RE = re.compile(rf"\(\s*({KEY})(?:\s+|\s*=\s*)(?:{NUMBER}|(true|false|null))\s*\)")
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


def values_match(cited, ref) -> bool:
    """The JSON-block rule: numbers within 1%, null <-> None, bools/strings exact, lists element-wise."""
    if ref is None or cited is None:
        return ref is None and cited is None
    if isinstance(ref, bool) or isinstance(cited, bool):
        return type(ref) is type(cited) and ref == cited
    if isinstance(ref, (int, float)) and isinstance(cited, (int, float)):
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


def check_json_block(agent: str, text: str, sources: dict[str, dict]) -> list[str]:
    blocks = JSON_BLOCK_RE.findall(text)
    if not blocks:
        return [f"{agent}: no ```json block found"]
    try:
        block = json.loads(blocks[-1])
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
    return failures


def _number_failures(number: tuple, found: dict[str, tuple]) -> list[str]:
    """[] when the printed number (NUMBER's four groups) fits one of the cited keys, else why not, per key."""
    sign, inner_sign, digits, unit = number
    negative = any(c in sign + inner_sign for c in "-−")
    digits, unit = digits.replace(",", ""), unit or ""
    shown = f"{'-' if negative else ''}{digits}{unit}"
    factor = UNIT_FACTORS[unit]
    why = []
    for key, (where, ref) in found.items():
        if ref is None:
            why.append(f"{key} cited {shown} for a null field (cited a value for a null field)")
            continue
        refs = ref if isinstance(ref, list) else [ref]  # a list reference: the number may be any element
        nums = [r for r in refs if isinstance(r, (int, float)) and not isinstance(r, bool)]
        if not nums:  # a text/date/bool field: a number next to it is not a claim about it
            continue
        if any(_prose_match(digits, negative, r / factor) for r in nums):
            return []
        why.append(f"{key} cited {shown} vs {', '.join(f'{r / factor:.4g}{unit}' for r in nums)} in {where}")
    return why


def _resolve_all(agent: str, keys: list[str], sources: dict[str, dict], failures: list[str]) -> dict[str, tuple]:
    found = {}
    for key in keys:
        where, ref = resolve(key, sources)
        if ref is MISSING:
            failures.append(f"{agent}: prose cites unknown key ({key})")
        else:
            found[key] = (where, ref)
    return found


def check_prose(agent: str, text: str, sources: dict[str, dict]) -> list[str]:
    prose = JSON_BLOCK_RE.sub("", text)
    failures = []
    for m in CITATION_RE.finditer(prose):
        found = _resolve_all(agent, [k.strip() for k in m.group(1).split(",")], sources, failures)
        number = NUMBER_BEFORE_RE.search(prose[max(0, m.start() - 40):m.start()])
        if number and found:
            failures += [f"{agent}: {w}" for w in _number_failures(number.groups(), found)]
    for m in INLINE_RE.finditer(prose):
        key, literal = m.group(1), m.group(6)
        found = _resolve_all(agent, [key], sources, failures)
        if not found:
            continue
        if literal is None:
            failures += [f"{agent}: {w}" for w in _number_failures(m.groups()[1:5], found)]
        elif not values_match(json.loads(literal), found[key][1]):
            failures.append(f"{agent}: {key} cited {literal} vs {_show(found[key][1])} in {found[key][0]}")
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
