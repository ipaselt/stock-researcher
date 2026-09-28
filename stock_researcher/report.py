"""The report: a skeleton rendered from the numbers at `run` time, filled by `assemble` from the agent files
and the planner's verdict.md. Plain string building; the only markers are HTML comments on their own line.

Flow: `render_skeleton` -> data/<T>/skeleton.md; the research agents write data/<T>/<agent>.md; the planner
writes data/<T>/verdict.md; `assemble` -> reports/<T>-<date>.md with a flat `key: value` front-matter that
`ledger.rebuild` reads back.
"""
import json
import math
import re
from pathlib import Path

from . import fair_value
from .scorecard import CATEGORY_WEIGHTS, METRICS

AGENTS = ["valuation", "growth-quality", "balance-sheet-risk", "technicals", "news-catalysts"]
OPTIONAL_AGENTS = ["bear-case"]
VERDICT_MARKER = "<!-- VERDICT -->"
SYNTHESIS_MARKER = "<!-- SYNTHESIS -->"
ASSEMBLY_MARKER = "<!-- ASSEMBLY WARNINGS -->"
CITATION_LINE = "citation check: not run"
LABELS = {"BUY", "SELL", "WAIT", "HAS RUN", "NOT LOOKING"}
VERDICT_KEYS = ("label_final", "entry_target", "override_reason")
FRONT_MATTER_KEYS = ("date", "ticker", "price", "score", "coverage", "fair_value", "entry", "label_suggested",
                     "rule_id", "label_final", "override_reason", "report")
# Scorecard fields stored as multiples (shown as "12.3x"); every other scorecard field is a fraction (shown as %).
MULTIPLES = {"valuation.forward_pe", "valuation.peg", "valuation.ev_ebitda", "health.debt_to_equity",
             "health.current_ratio", "health.interest_coverage", "health.cash_to_debt"}
AGENT_SECTIONS = [
    ("Valuation", "valuation"),
    ("Growth and quality", "growth-quality"),
    ("Balance sheet and risk", "balance-sheet-risk"),
    ("Technicals and timing", "technicals"),
    ("News and catalysts", "news-catalysts"),
    ("Bear case", "bear-case"),
]
DISCLAIMER = "This report is generated research for the owner's own process. It is not investment advice."
LIMITS_HEADING = "Stated limits (copied into every report):"
STATED_LIMITS = fair_value.__doc__.split(LIMITS_HEADING, 1)[1].strip()  # the one source: the module docstring


MARKER_RE = re.compile(r"^(<!-- (?:AGENT: [a-z-]+|VERDICT|SYNTHESIS|ASSEMBLY WARNINGS) -->)$", re.MULTILINE)
QUOTE_KEYS = {"override_reason"}  # free text: always written as a JSON (= YAML double-quoted) string


def slot(agent: str) -> str:
    return f"<!-- AGENT: {agent} -->"


def section_block(heading: str, agent: str) -> str:
    """The exact skeleton text of an agent section, as `render_skeleton` writes it (joined by a blank line)."""
    return f"## {heading}\n\n{slot(agent)}\n"


# --- formatting helpers ---------------------------------------------------------------------------------

def fmt_money(v: float | None) -> str:
    """Dollars to cents; below $1 to 4 decimals so a sub-penny price does not print as $0.00."""
    if v is None:
        return "—"
    return f"${v:,.4f}" if abs(v) < 1 else f"${v:,.2f}"


def fmt_pct(v: float | None) -> str:
    return "—" if v is None else f"{v:.1%}"


def fmt_value(field: str, v: float | None) -> str:
    """A scorecard value by kind: multiples as `x`, fractions as %, missing as an em dash."""
    if v is None:
        return "—"
    return f"{v:.1f}x" if field in MULTIPLES else fmt_pct(v)


def _num(v) -> str:
    """A front-matter value: numbers as-is (money rounded to cents by the caller), None as `none`."""
    return "none" if v is None else str(v)


def _round(v: float | None, places: int = 2) -> float | None:
    return None if v is None else round(v, places)


# --- front-matter (flat `key: value` lines between `---` fences) -----------------------------------------

def _yaml_value(key: str, value: str) -> str:
    if key in QUOTE_KEYS or any(c in value for c in ':#"\'') or value != value.strip():
        return json.dumps(value, ensure_ascii=False)
    return value


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] == '"':
        try:
            return json.loads(value)
        except ValueError:
            return value
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1]
    return value


def is_none(value: str | None) -> bool:
    return value is None or value.strip().lower() in ("", "none")


def front_matter(values: dict) -> str:
    return "---\n" + "".join(f"{k}: {_yaml_value(k, str(v))}\n" for k, v in values.items()) + "---\n"


def parse_front_matter(text: str) -> tuple[dict, str] | None:
    """(fields, body) when `text` opens with a `---` fenced block of `key: value` lines, else None."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    fields = {}
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return fields, "\n".join(lines[i + 1:])
        if not line.strip():
            continue
        key, sep, value = line.partition(":")
        if not sep or not key.strip():
            return None
        fields[key.strip()] = _unquote(value.strip())
    return None  # no closing fence


# --- skeleton ---------------------------------------------------------------------------------------------

def _header(s) -> str:
    m = s.meta
    cap = "—" if m.market_cap is None else f"${m.market_cap / 1e9:,.1f}B"
    rows = [
        ("Ticker", m.ticker), ("Name", m.name or "—"),
        ("Sector / industry", f"{m.sector or '—'} / {m.industry or '—'}"),
        ("Price", fmt_money(m.price)), ("Market cap", cap), ("Run date", m.as_of or "—"),
        ("Provider", m.provider or "—"), ("Data as of", f"{m.as_of or '—'} (provider snapshot at run time)"),
    ]
    return "## Header\n\n| Field | Value |\n|---|---|\n" + "".join(f"| {k} | {v} |\n" for k, v in rows)


def _verdict(score, fv, label) -> str:
    total = "—" if score.total is None else f"{score.total:.1f}/100 ({score.band_word})"
    band = "" if fv.band_low is None else f" (band {fmt_money(fv.band_low)} – {fmt_money(fv.band_high)})"
    rows = [
        ("Suggested label", f"{label.label} ({label.rule_id})"), ("Score", total),
        ("Coverage", f"{score.coverage_pct:.0%}"), ("Fair value", fmt_money(fv.fair_value) + band),
        ("Entry target", fmt_money(label.entry_target)), ("Upside to fair value", fmt_pct(fv.upside)),
    ]
    table = "| Item | Value |\n|---|---|\n" + "".join(f"| {k} | {v} |\n" for k, v in rows)
    return f"## Verdict\n\n{table}\n{VERDICT_MARKER}\n"


def _scorecard(score) -> str:
    out = ["## Scorecard\n", "| Category | Metric | Value | Grade | Points | Weight | Note |",
           "|---|---|---|---|---|---|---|"]
    for r in score.metrics:
        points = "—" if r.points is None else f"{r.points:g}"
        out.append(f"| {r.category} | `{r.field.split('.')[1]}` | {fmt_value(r.field, r.value)} | "
                   f"{r.grade or '—'} | {points} | {r.weight} | {r.note or ''} |")
    out += ["", "| Category | Weight | Subscore | Coverage |", "|---|---|---|---|"]
    for name, c in score.categories.items():
        sub = "—" if c.score is None else f"{c.score:.1f}"
        out.append(f"| {name} | {CATEGORY_WEIGHTS[name]} | {sub} | {c.coverage:.0%} |")
    return "\n".join(out) + "\n"


def score_table(score, fv, label) -> str:
    """The scorecard as fixed-width plain text (`score --table`): one row per metric, a line per category,
    then the fair value and the suggested label. Values are formatted as in the report."""
    rows = [("category", "metric", "value", "grade", "pts", "wt", "note")]
    for r in score.metrics:
        rows.append((r.category, r.field, fmt_value(r.field, r.value), r.grade or "—",
                     "—" if r.points is None else f"{r.points:g}", str(r.weight), r.note or ""))
    widths = [max(len(row[i]) for row in rows) for i in range(len(rows[0]))]
    rows.insert(1, tuple("-" * w for w in widths))
    lines = ["  ".join(cell.ljust(w) for cell, w in zip(row, widths)).rstrip() for row in rows]
    lines.append("")
    for name, c in score.categories.items():
        sub = "—" if c.score is None else f"{c.score:.1f}"
        lines.append(f"{name:<13} weight {CATEGORY_WEIGHTS[name]:>2}  score {sub:>5}  coverage {c.coverage:.0%}")
    lines.append("")
    if fv.fair_value is None:
        lines.append(f"fair value —: {fv.reason} (fair P/E {fv.fair_pe:.1f}x)")
    else:
        lines.append(f"fair value {fmt_money(fv.fair_value)} (band {fmt_money(fv.band_low)} – "
                     f"{fmt_money(fv.band_high)}), fair P/E {fv.fair_pe:.1f}x ({fv.fair_pe_source.replace('_', ' ')}, "
                     f"{fv.n_years}y), margin of safety {fv.margin_of_safety:.0%}, entry {fmt_money(fv.entry_price)}, "
                     f"upside {fmt_pct(fv.upside)}")
    lines.append(f"label {label.label} ({label.rule_id}): {label.reason}")
    return "\n".join(lines)


def _mos_why(total: float | None) -> str:
    if total is None:
        return "no score, so the default tier applies"
    for min_score, _ in fair_value.MOS_TIERS:
        if total >= min_score:
            return f"score {total:.1f} is at or above {min_score}"
    return f"score {total:.1f} is below {fair_value.MOS_TIERS[-1][0]}"


def _mos_tiers() -> str:
    tiers = [f"score ≥ {min_score} → {mos:.0%}" for min_score, mos in fair_value.MOS_TIERS]
    return ", ".join(tiers + [f"otherwise {fair_value.MOS_DEFAULT:.0%}"])


def _fair_value(snapshot, score, fv) -> str:
    if fv.fair_pe_source == "historical_median":
        source = f"the median year-end P/E of the last {fv.n_years} fiscal years"
    else:
        source = (f"the sector default for {snapshot.meta.sector or 'an unknown sector'} "
                  f"(only {fv.n_years} usable fiscal years; {fair_value.MIN_YEARS} needed)")
    fair_pe = f"fair P/E {fv.fair_pe:.1f}x, from {source}"
    if fv.fair_value is None:
        body = f"No fair value: {fv.reason}. For reference, the {fair_pe}. No entry price is set.\n"
    else:
        mos = f"{fv.margin_of_safety:.0%}"
        body = (
            f"- Fair value = forward EPS {fmt_money(fv.forward_eps)} × {fair_pe} = **{fmt_money(fv.fair_value)}**.\n"
            f"- Band ±{fair_value.BAND:.0%}: {fmt_money(fv.band_low)} – {fmt_money(fv.band_high)}.\n"
            f"- Margin of safety {mos}: {_mos_why(score.total)} (tiers: {_mos_tiers()}).\n"
            f"- Entry price = {fmt_money(fv.fair_value)} × (1 − {mos}) = **{fmt_money(fv.entry_price)}**.\n"
            f"- Upside from the price {fmt_money(snapshot.meta.price)} to fair value: {fmt_pct(fv.upside)}.\n"
        )
    return f"## Fair value and entry price\n\n{body}\n{LIMITS_HEADING}\n\n{STATED_LIMITS}\n"


def _appendix(snapshot) -> str:
    def bullets(items):
        return "".join(f"- {i}\n" for i in items) if items else "- none\n"

    return (
        "## Appendix\n\n"
        f"Fields missing:\n\n{bullets(snapshot.meta.fields_missing)}\n"
        f"Warnings:\n\n{bullets(snapshot.meta.warnings)}\n"
        f"{ASSEMBLY_MARKER}\n\n"
        "citation check: not run\n\n"
        "Methodology: [scorecard](../docs/scorecard.md) · [fair value](../docs/fair-value.md) · "
        "[labels](../docs/labels.md)\n\n"
        f"{DISCLAIMER}\n"
    )


def render_skeleton(snapshot, score, fv, label) -> str:
    m = snapshot.meta
    parts = [f"# {m.ticker} — {m.name or m.ticker}\n", _header(snapshot), _verdict(score, fv, label),
             _scorecard(score), _fair_value(snapshot, score, fv)]
    parts += [section_block(heading, agent) for heading, agent in AGENT_SECTIONS]
    parts.append(f"## Synthesis\n\nRule fired: **{label.rule_id}** ({label.label}): {label.reason}.\n\n"
                 f"{SYNTHESIS_MARKER}\n")
    parts.append(_appendix(snapshot))
    return "\n".join(parts)


# --- assemble ---------------------------------------------------------------------------------------------

def _read(path: Path, what: str, encoding: str = "utf-8") -> str:
    if not path.exists():
        raise FileNotFoundError(f"missing {what}: {path.as_posix()}")
    return path.read_text(encoding=encoding)


def _split_thesis(body: str) -> tuple[str | None, str]:
    """(the `### Thesis` section's text or None when there is no such heading, the rest of the verdict body)."""
    lines = body.strip().splitlines()
    start = next((i for i, line in enumerate(lines) if line.strip() == "### Thesis"), None)
    if start is None:
        return None, body.strip()
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("### ")), len(lines))
    thesis = "\n".join(lines[start + 1:end]).strip()
    rest = "\n".join(lines[:start] + lines[end:]).strip()
    return thesis, rest


def _fill(skeleton: str, fills: dict[str, str]) -> str:
    """Replace each marker line of the skeleton exactly once; inserted text is never scanned for markers."""
    parts = MARKER_RE.split(skeleton)  # odd indexes are the markers themselves
    return "".join(fills.get(part, part) if i % 2 else part for i, part in enumerate(parts))


def _parse_verdict(text: str, label_suggested: str) -> tuple[dict, str]:
    parsed = parse_front_matter(text)
    if parsed is None:
        raise ValueError("verdict.md has no front-matter (--- fenced key: value lines)")
    fields, body = parsed
    missing = [k for k in VERDICT_KEYS if not fields.get(k)]
    if missing:
        raise ValueError(f"verdict.md front-matter missing {', '.join(missing)}")
    if fields["label_final"] not in LABELS:
        raise ValueError(f"verdict.md label_final {fields['label_final']!r} is not one of {sorted(LABELS)}")
    if fields["label_final"] != label_suggested and is_none(fields["override_reason"]):
        raise ValueError("verdict.md overrides the suggested label without an override_reason")
    if not is_none(fields["entry_target"]):
        try:
            ok = math.isfinite(float(fields["entry_target"]))
        except ValueError:
            ok = False
        if not ok:
            raise ValueError(f"verdict.md entry_target {fields['entry_target']!r} is not a number or none")
    if not body.strip():
        raise ValueError("verdict.md body is empty")
    return fields, body


def _citations(path: Path, born: float, reported: dict[str, float], warnings: list[str]) -> dict[str, list] | None:
    """{agent: failure lines} for the reported agents, from citations.json when it is current and well-formed.

    `reported` maps each agent whose file goes into the report to that file's mtime; a dropped (empty) agent's
    result is left out. None (the check counts as not run, with a warning) when citations.json is missing, older
    than skeleton.md or a reported agent file (it describes other files), or not the shape verify-citations writes.
    """
    if not path.exists():
        return None
    if path.stat().st_mtime < max([born, *reported.values()]):
        warnings.append("stale citations.json ignored (older than skeleton.md or an agent file; re-run verify-citations)")
        return None
    try:
        results = json.loads(path.read_text(encoding="utf-8"))
        ok = isinstance(results, dict) and all(
            isinstance(r, dict) and r.get("status") in ("PASS", "FAIL") and isinstance(r.get("failures"), list)
            and (r["status"] == "PASS") == (not r["failures"]) for r in results.values())
    except ValueError:
        ok = False
    if not ok:
        warnings.append("unreadable citations.json ignored (re-run verify-citations)")
        return None
    return {a: r["failures"] for a, r in results.items() if a in reported}


def _citation_line(results: dict[str, list] | None, n_reported: int) -> str:
    if results is None:
        return CITATION_LINE
    failed = {agent: f for agent, f in results.items() if f}
    if failed:
        listed = "; ".join(f"{a}: {len(f)} mismatch{'es' if len(f) != 1 else ''}" for a, f in failed.items())
        return f"citation check: FAIL — {listed}"
    return f"citation check: PASS ({len(results)}/{n_reported} agents)"  # an unchecked agent shows as a gap


def assemble(ticker: str, data_dir: Path, reports_dir: Path, today: str) -> Path:
    """Fill data/<T>/skeleton.md from the agent files and verdict.md; write reports/<T>-<today>.md.

    A file older than skeleton.md belongs to an earlier run: a stale agent file counts as not reported, a stale
    verdict.md is an error.
    """
    data_dir, reports_dir = Path(data_dir), Path(reports_dir)
    run_dir = data_dir / ticker
    skeleton_path = run_dir / "skeleton.md"
    text = _read(skeleton_path, "skeleton (run `run` first)")
    born = skeleton_path.stat().st_mtime
    result = json.loads(_read(data_dir / f"{ticker}.score.json", "score file"))
    suggestion, fv = result["label_suggestion"], result["fair_value"]
    verdict_path = run_dir / "verdict.md"
    verdict_text = _read(verdict_path, "verdict", encoding="utf-8-sig")
    if verdict_path.stat().st_mtime < born:
        raise ValueError(f"stale verdict: {verdict_path.as_posix()} is older than skeleton.md (from an earlier run)")
    fields, body = _parse_verdict(verdict_text, suggestion["label"])

    warnings, fills, reported = [], {}, {}
    for heading, agent in AGENT_SECTIONS:
        path = run_dir / f"{agent}.md"
        content = ""
        if path.exists():
            if path.stat().st_mtime < born:
                warnings.append(f"stale {path.name} ignored (older than skeleton.md)")
            else:
                content = path.read_text(encoding="utf-8").strip()
        if content:
            fills[slot(agent)] = content
            reported[agent] = path.stat().st_mtime
        elif agent in OPTIONAL_AGENTS:
            block = section_block(heading, agent) + "\n"
            if text.count(block) != 1:
                raise ValueError(f"skeleton.md does not contain the {heading!r} section exactly once")
            text = text.replace(block, "")
        else:
            fills[slot(agent)] = "_(agent did not report)_"
            warnings.append(f"{agent} agent did not report")

    checked = _citations(run_dir / "citations.json", born, reported, warnings)
    for agent, failures in (checked or {}).items():
        if failures:  # a failing agent's numbers are not published
            fills[slot(agent)] = "_(agent failed citation check)_"
            warnings.append(f"{agent} failed the citation check; its section is withheld")
    if text.count(CITATION_LINE) != 1:
        raise ValueError(f"skeleton.md does not contain {CITATION_LINE!r} exactly once")
    text = text.replace(CITATION_LINE, _citation_line(checked, len(reported)))
    thesis, rest = _split_thesis(body)
    if thesis is None:
        warnings.append("verdict.md has no '### Thesis' heading")
    label_final, override = fields["label_final"], fields["override_reason"]
    reason = "" if is_none(override) else f": {override}"
    verb = "confirms" if label_final == suggestion["label"] else "overrides"
    how = f"{verb} the suggested {suggestion['label']} ({suggestion['rule_id']}){reason}"
    entry = fields["entry_target"]
    entry_line = "none" if is_none(entry) else fmt_money(float(entry))
    verdict = f"**Final label: {label_final}** (entry target {entry_line}); {how}.\n\n{thesis or ''}"
    fills[VERDICT_MARKER] = verdict.rstrip()
    fills[SYNTHESIS_MARKER] = rest
    notes = "".join(f"- {w}\n" for w in warnings) if warnings else "- none\n"
    fills[ASSEMBLY_MARKER] = f"Assembly warnings:\n\n{notes}".rstrip()
    text = _fill(text, fills)

    name = f"{ticker}-{today}.md"
    values = {
        "date": today, "ticker": ticker, "price": _num(result["price"]), "score": _num(result["total"]),
        "coverage": _num(result["coverage_pct"]), "fair_value": _num(_round(fv["fair_value"])),
        "entry": "none" if is_none(entry) else _num(_round(float(entry))),
        "label_suggested": suggestion["label"], "rule_id": suggestion["rule_id"], "label_final": label_final,
        "override_reason": "none" if is_none(override) else override, "report": f"{reports_dir.name}/{name}",
    }
    reports_dir.mkdir(parents=True, exist_ok=True)
    out = reports_dir / name
    out.write_text(front_matter(values) + "\n" + text, encoding="utf-8")
    return out
