"""The research agents and /research command are prompts, but their frontmatter and shared contract are pinned here
so they cannot drift (spec: planning/research/agent-contract.md, planning/research/research-command.md)."""
from pathlib import Path

import pytest

from stock_researcher.report import AGENTS, OPTIONAL_AGENTS

CLAUDE = Path(__file__).parent.parent / ".claude"
AGENT_DIR = CLAUDE / "agents"
COMMAND = CLAUDE / "commands" / "research.md"
CONTRACT_SPEC = CLAUDE.parent / "planning" / "research" / "agent-contract.md"
AGENT_FILES = sorted(AGENT_DIR.glob("*.md"))
HARD_RULES = ("Cite, never compute", "Units:", "Scope:", "No fetching", "Write exactly one file")
BASE_TOOLS = {"Read", "Write"}
EXPECTED_TOOLS = {name: BASE_TOOLS for name in AGENTS + OPTIONAL_AGENTS}
EXPECTED_TOOLS["news-catalysts"] = BASE_TOOLS | {"WebSearch", "WebFetch"}


def split_frontmatter(path: Path) -> tuple[dict, str]:
    """(`key: value` frontmatter fields, body). Hand-rolled: the file opens with a `---` fenced block."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    assert lines[0] == "---", f"{path.name}: no opening --- fence"
    end = lines.index("---", 1)
    fields = {}
    for line in lines[1:end]:
        key, sep, value = line.partition(":")
        assert sep, f"{path.name}: frontmatter line without a colon: {line!r}"
        assert key.strip() not in fields, f"{path.name}: duplicate frontmatter key {key.strip()!r}"
        fields[key.strip()] = value.strip()
    return fields, "\n".join(lines[end + 1:])


def tool_set(value: str) -> set[str]:
    return {t.strip() for t in value.split(",") if t.strip()}


def shared_body(body: str) -> str:
    """The contract text: from the first line after the frontmatter up to the `## Focus` heading."""
    assert body.count("\n## Focus\n") == 1, "expected exactly one '## Focus' heading"
    return body.split("\n## Focus\n", 1)[0]


def test_agent_files_match_report_agents():
    assert {p.stem for p in AGENT_FILES} == set(AGENTS + OPTIONAL_AGENTS)


@pytest.mark.parametrize("path", AGENT_FILES, ids=lambda p: p.stem)
def test_agent_frontmatter(path):
    fields, _ = split_frontmatter(path)
    assert fields["name"] == path.stem
    assert fields["description"]
    assert fields["model"] == "opus"
    assert fields["effort"] == "high"
    assert tool_set(fields["tools"]) == EXPECTED_TOOLS[path.stem]
    assert {"Bash", "Edit", "Agent"} <= tool_set(fields["disallowedTools"])
    assert not tool_set(fields["tools"]) & tool_set(fields["disallowedTools"])


@pytest.mark.parametrize("path", AGENT_FILES, ids=lambda p: p.stem)
def test_agent_body_carries_contract(path):
    _, body = split_frontmatter(path)
    contract = shared_body(body)
    for anchor in HARD_RULES:
        assert anchor in contract, f"{path.name}: hard rule {anchor!r} missing"
    assert '"numbers_cited"' in contract
    focus = body.split("\n## Focus\n", 1)[1]
    assert f"**{path.stem}**" in focus, f"{path.name}: Focus block is not this agent's"


def test_shared_body_identical_across_agents():
    bodies = {p.stem: shared_body(split_frontmatter(p)[1]) for p in AGENT_FILES}
    reference = bodies["valuation"]
    diverged = [name for name, body in bodies.items() if body != reference]
    assert not diverged, f"shared contract diverges from valuation.md in: {diverged}"


def spec_shared_body() -> str:
    """The spec's "Shared body" section, with its 3-backtick outer output-format fence widened to 4 (as the agent files
    carry it, so the nested ```json fence renders)."""
    spec = CONTRACT_SPEC.read_text(encoding="utf-8")
    body = spec.split("## Shared body (verbatim in every agent)\n", 1)[1].split("\n## Per-agent Focus blocks", 1)[0]
    body = body.replace("**Output file format** (`data/<T>/<your-name>.md`)\n```\n",
                        "**Output file format** (`data/<T>/<your-name>.md`)\n````\n", 1)
    return body.replace("```\n```\n`numbers_cited`", "```\n````\n`numbers_cited`", 1).strip()


def test_shared_body_matches_spec():
    agent = shared_body(split_frontmatter(AGENT_DIR / "valuation.md")[1]).strip()
    assert agent == spec_shared_body(), "valuation.md shared contract drifted from planning/research/agent-contract.md"


def test_research_command():
    fields, body = split_frontmatter(COMMAND)
    assert fields["description"]
    assert fields["argument-hint"] == "[TICKER]"
    assert "stock_researcher" in fields["allowed-tools"]
    assert fields["disable-model-invocation"] == "true"
    for word in ("stock_researcher run", "stock_researcher verify-citations", "stock_researcher assemble",
                 "reports/ratings.csv", "verdict.md", "$ARGUMENTS"):
        assert word in body, f"research.md body missing {word!r}"
    missing = [a for a in AGENTS if f"`{a}`" not in body]
    assert not missing, f"research.md does not name agents: {missing}"
