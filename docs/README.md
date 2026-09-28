# docs/

The methodology, written for a reader who did not build the tool (an interviewer, a future you):

- `scorecard.md` — categories, weights, every threshold band, the coverage rule (arrives with slice S3)
- `fair-value.md` — the entry-price method and its stated limits (S3)
- `labels.md` — BUY / SELL / WAIT / HAS RUN / NOT LOOKING rules L1-L8 and the override protocol (S3)

`tests/test_docs.py` asserts every metric and weight in `stock_researcher/scorecard.py` appears here, so
these files cannot drift from the code. ADRs live in `memory/decisions.md`; the approved design in
`planning/plans/`.
