# Project 1 demonstration and expected behavior

Run from the repository root after installing `requirements-project1.txt`.

## Required live run

1. Configure `.env` with a real Groq key. Run `python demo_project1.py`.
2. Reject the baseline topic save if you want the comparison to start without reusable memory.
3. Approve the two learning-preference records: `preferred_style=bullet_points` and `level=intermediate`.
4. Complete the normal and later requests. Inspect source-note results and retrieved memory. The later request uses another thread ID with no previous conversation history.
5. Approve the correction to `preferred_style=worked_examples`; inspect the incremented revision and the later request using that format.
6. Reject the final proposed `level=advanced` change. Verify the before/after records match and the route ends in `reject_memory`.
7. Save the generated `demo_runs/<run-id>/evidence.json` and relevant screenshots for the report/live demonstration. If a provider request fails, resolve it and repeat; do not submit simulated model output as live evidence.

The CLI asks for actual decisions by default. Choosing a different decision changes the outcome; it does not force the expected answer. Use the Streamlit application to demonstrate the same behavior visually.

## Expected versus actual evidence

| Case | Expected behavior | Offline result |
|---|---|---|
| Baseline without saved preferences | Defaults used; no previous approved records | Verified with simulated model |
| Store two records | No records before approval; separate style and level rows after approval | Verified with real SQLite |
| Normal tutoring request | Read permitted notes, generate answer, review last-topic proposal | Verified; model response simulated |
| Later request / new thread | Empty chat; retrieve earlier records; include saved style/level in prompt | Verified with real thread separation and simulated model |
| Correction | Preserve old value before approval; replace same record and increment revision after approval | Verified with real SQLite |
| Later request after correction | Use corrected preference in the prompt | Verified; model response simulated |
| Rejection | Do not change reusable memory or save quiz progress | Verified with real graph rejection branch |
| Invalid approval such as `"no"` | Reject non-boolean payload; no writes | Verified |
| Missing notes / malformed quiz | Explain the limitation; do not invent sources or save success | Verified |
| Another simulated learner | Ordinary retrieval returns only that learner's records | Verified; this is not production authentication |

`docs/project1_simulation_evidence.json` is an actual offline run with **scripted** decisions, clearly labeled. `docs/project1_test_results.txt` records the automated test outcome. Neither substitutes for the required working live LLM and human demonstration.

## Submission checklist

- [ ] Confirm team size (1–3) with the instructor.
- [ ] Run the live demonstration and retain actual input/output/rejection evidence.
- [ ] Finalize the 1–2 page report and truthful individual contributions.
- [ ] Include the architecture diagram and source/dependency snapshot.
- [ ] Inspect the submission for keys and use authorized/sample materials only.
