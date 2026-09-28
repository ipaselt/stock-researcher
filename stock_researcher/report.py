"""The report: a skeleton rendered from the numbers at `run` time, filled by `assemble` from the agent files
and the planner's verdict.md. Plain string building; the only markers are HTML comments on their own line.

Flow: `render_skeleton` -> data/<T>/skeleton.md; the research agents write data/<T>/<agent>.md; the planner
writes data/<T>/verdict.md; `assemble` -> reports/<T>-<date>.md with a flat `key: value` front-matter that
`ledger.rebuild` reads back.
"""
import json
import math
from pathlib import Path

from . import fair_value
from .scorecard import CATEGORY_WEIGHTS, METRICS

AGENTS = ["valuation", "growth-quality", "balance-sheet-risk", "technicals", "news-catalysts"]
OPTIONAL_AGENTS = ["bear-case"]
VERDICT_MARKER = "<!-- VERDICT -->"
SYNTHESIS_MARKER = "<!-- SYNTHESIS -->"
ASSEMBLY_MARKER = "<!-- ASSEMBLY WARNINGS -->"
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


def slot(agent: str) -> str:
    return f"<!-- AGENT: {agent} -->"


# --- formatting helpers ---------------------------------------------------------------------------------

def fmt_money(v: float | None) -> str:
    return "—" if v is None else f"${v:,.2f}"


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

def front_matter(values: dict) -> str:
    return "---\n" + "".join(f"{k}: {v}\n" for k, v in values.items()) + "---\n"


def parse_front_matter(text: str) -> tuple[dict, str] | None:
    """(fields, body) when `text` opens with a `---` fenced block of `key: value` lines, else None."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    fields = {}
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return fields, "\n".join(lines[i + 1:])
        key, sep, value = line.partition(":")
        if not sep or not key.strip():
            return None
        fields[key.strip()] = value.strip()
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
    parts += [f"## {heading}\n\n{slot(agent)}\n" for heading, agent in AGENT_SECTIONS]
    parts.append(f"## Synthesis\n\nRule fired: **{label.rule_id}** ({label.label}): {label.reason}.\n\n"
                 f"{SYNTHESIS_MARKER}\n")
    parts.append(_appendix(snapshot))
    return "\n".join(parts)


# --- assemble ---------------------------------------------------------------------------------------------

def _read(path: Path, what: str) -> str:
    if not path.exists():
        raise FileNotFoundError(f"missing {what}: {path.as_posix()}")
    return path.read_text(encoding="utf-8")


def _split_thesis(body: str) -> tuple[str, str]:
    """(the `### Thesis` section's text, the rest of the verdict body)."""
    lines = body.strip().splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == "### Thesis")
    except StopIteration:
        return "", body.strip()
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("### ")), len(lines))
    thesis = "\n".join(lines[start + 1:end]).strip()
    rest = "\n".join(lines[:start] + lines[end:]).strip()
    return thesis, rest


def _drop_section(text: str, heading: str) -> str:
    """Remove `## heading` and everything up to the next `## ` heading."""
    start = text.index(f"## {heading}\n")
    end = text.index("\n## ", start + 1) + 1
    return text[:start] + text[end:]


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
    if fields["label_final"] != label_suggested and fields["override_reason"].lower() == "none":
        raise ValueError("verdict.md overrides the suggested label without an override_reason")
    if fields["entry_target"].lower() != "none":
        try:
            ok = math.isfinite(float(fields["entry_target"]))
        except ValueError:
            ok = False
        if not ok:
            raise ValueError(f"verdict.md entry_target {fields['entry_target']!r} is not a number or none")
    if not body.strip():
        raise ValueError("verdict.md body is empty")
    return fields, body


def assemble(ticker: str, data_dir: Path, reports_dir: Path, today: str) -> Path:
    """Fill data/<T>/skeleton.md from the agent files and verdict.md; write reports/<T>-<today>.md."""
    data_dir, reports_dir = Path(data_dir), Path(reports_dir)
    run_dir = data_dir / ticker
    text = _read(run_dir / "skeleton.md", "skeleton (run `run` first)")
    result = json.loads(_read(data_dir / f"{ticker}.score.json", "score file"))
    suggestion, fv = result["label_suggestion"], result["fair_value"]
    fields, body = _parse_verdict(_read(run_dir / "verdict.md", "verdict"), suggestion["label"])

    warnings = []
    for agent in AGENTS + OPTIONAL_AGENTS:
        path = run_dir / f"{agent}.md"
        content = path.read_text(encoding="utf-8").strip() if path.exists() else ""
        if content:
            text = text.replace(slot(agent), content)
        elif agent in OPTIONAL_AGENTS:
            heading = next(h for h, a in AGENT_SECTIONS if a == agent)
            text = _drop_section(text, heading)
        else:
            text = text.replace(slot(agent), "_(agent did not report)_")
            warnings.append(f"{agent} agent did not report")

    thesis, rest = _split_thesis(body)
    label_final, override = fields["label_final"], fields["override_reason"]
    if override.lower() == "none":
        how = f"confirms the suggested {suggestion['label']} ({suggestion['rule_id']})"
    else:
        how = f"overrides the suggested {suggestion['label']} ({suggestion['rule_id']}): {override}"
    entry = fields["entry_target"]
    entry_line = "none" if entry.lower() == "none" else fmt_money(float(entry))
    verdict = f"**Final label: {label_final}** (entry target {entry_line}); {how}.\n\n{thesis}".rstrip()
    text = text.replace(VERDICT_MARKER, verdict).replace(SYNTHESIS_MARKER, rest)
    notes = "".join(f"- {w}\n" for w in warnings) if warnings else "- none\n"
    text = text.replace(ASSEMBLY_MARKER, f"Assembly warnings:\n\n{notes}".rstrip())

    name = f"{ticker}-{today}.md"
    values = {
        "date": today, "ticker": ticker, "price": _num(result["price"]), "score": _num(result["total"]),
        "coverage": _num(result["coverage_pct"]), "fair_value": _num(_round(fv["fair_value"])),
        "entry": "none" if entry.lower() == "none" else _num(_round(float(entry))),
        "label_suggested": suggestion["label"], "rule_id": suggestion["rule_id"], "label_final": label_final,
        "override_reason": override, "report": f"{reports_dir.name}/{name}",
    }
    reports_dir.mkdir(parents=True, exist_ok=True)
    out = reports_dir / name
    out.write_text(front_matter(values) + "\n" + text, encoding="utf-8")
    return out
