# Fixtures

`ctd_m4_55_percent_completeness_test.pdf` and `m4_55_percent_completeness_demo.pdf`
are **reconstructions**, not the originally reported files. The actual uploaded
fixtures were never present in this environment's filesystem (confirmed by a
full-disk search), so these were regenerated from the live ICH M4 knowledge base
to reproduce the same reported failure mode: a 5-page PDF containing only a table
of section ID / title / status-label rows, with zero real narrative or technical
content behind any row.

If the original files become available, replace these and re-run
`tests/test_m4_substance_gate.py` / `tests/test_m4_guideline_checker.py` against them.
