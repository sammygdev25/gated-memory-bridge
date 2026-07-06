# Supplementary Evaluation Materials

This directory holds the machine-readable evaluation artifacts referenced by the paper's
Reproducibility Statement. Human-readable versions (transcripts, scoring tables, traces,
iteration log) are Appendices B–G of the paper itself.



## File manifest


| File | Contents | Paper reference |
|---|---|---|
| `s55a_setup.py` | Creates test user + 6 sessions with ground truth | Appendix B |
| `s55a_regression_check.py` | 4-field regression / pilot runner | Section 6.2, Appendix G |
| `s55a_scored_runs.py` | 18 scored extraction runs | Section 7.1, Appendix C |
| `s55a_scoring.py` | Scoring pass (all metrics) | Appendix D |
| `s55a_supersession_test.py` | Supersession protocol | Section 7.4, Appendix E |
| `s55a_naive_vs_gated.py` | Single-session comparison | Section 7.5.1, Appendix F |
| `s55a_multisession.py` | Multi-session comparison + token counts | Section 7.5.2–7.5.3 |
| `s55a_cleanup.py` | Test-data teardown | Section 6.1 |
| `scored_runs_raw.json` | Raw JSON from all 18 extraction runs | Appendices C, D |
| `scoring_results.json` | Machine-readable scoring output | Appendix D |
| `session_ids.json` | Session ID map for the test corpus | (none) |
| `naive_vs_gated_results.json` | Comparison raw outputs | Appendix F |
| `multisession_results.json` | Multi-session raw outputs | Appendix F |

## Data and redaction notes

The test corpus is fully synthetic (paper, Appendix B) and contains no user data.
The scripts reference internal module paths (`api.tasks.chat_memory`, etc.); these
are import names only.

One redaction: the test-user password in `s55a_setup.py` has been replaced with
a placeholder (`CHANGE_ME_EVAL_PASSWORD`); substitute any value when reproducing.
The account it creates existed only in a local evaluation database and was
deleted after the evaluation.
