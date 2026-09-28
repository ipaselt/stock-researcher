# docs/

The methodology, written for a reader who did not build the tool (an interviewer, a future you):

- `scorecard.md` — categories, weights, every threshold band, the coverage rule
- `fair-value.md` — the entry-price method and its stated limits
- `labels.md` — BUY / SELL / WAIT / HAS RUN / NOT LOOKING rules L1-L8 and the override protocol

`tests/test_docs.py` asserts every metric, weight and band edge in `stock_researcher/scorecard.py`, every
constant in `fair_value.py` and `labels.py`, and the fair-value stated limits appear here, so these files
cannot drift from the code. ADRs live in `memory/decisions.md`; the approved design in `planning/plans/`.

The citation guard (`verify-citations`, `stock_researcher/citations.py`) states its rules in its module docstring;
`tests/test_citations.py` pins each one, including a x1.5 mutation of every decimal in two real agent outputs.
