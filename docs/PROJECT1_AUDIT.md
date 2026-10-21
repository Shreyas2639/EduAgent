# Project 1 requirement audit

Baseline inspected: `main` commit `e66ba4e86f879b904c9336d907ede108a9c2c703`.
Source of requirements: the supplied **ITS 58100 - Project requirement documentation-- Agentic AI.docx**. This audit covers Project 1 and applicable overall/submission requirements, not Project 2 or Final Project acceptance.

“Implemented” describes inspected code. “Verified offline” means real graph/storage/tool execution with simulated model responses. Neither means the live model was tested.

| Requirement | Baseline finding | Improvement / evidence |
|---|---|---|
| Narrow practical goal, inputs and outputs | Present: Python tutoring, quizzes, progress. Wider math/Wikipedia features complicate the story. | README defines the Python Fundamentals task and the demonstration scope. |
| Python and a working LLM | Groq calls are implemented; no live execution established by this audit. | Provider setup and model override documented; live verification still pending. |
| Stateful workflow with at least 3 functional steps | Present: safety → coordinator → intent-specific node. | Explicit start → memory load → safety → routing → source retrieval → tutoring, followed by memory review when applicable. |
| Meaningful tool/information source | Present: FAISS notes, SymPy and Wikipedia paths. | Project 1 retrieves real local notes in a visible graph node; no embedding download required. |
| Explicit state | Present: `AgentState`. | Adds source results, retrieved records, proposal, approval, active quiz and visible steps. |
| At least one conditional route | Present: safety and intent routes. | Retained; approval also branches to commit or reject. |
| Human approval/rejection point | Missing. Model safety refusal is not a human approval decision. | `interrupt()` pauses the graph; explicit boolean decision resumes to commit/reject. UI and interactive CLI provided. |
| Rejection demonstrated | Missing. | Automated rejection verifies unchanged records; interactive live demonstration still required. |
| Separate current-thread and reusable memory | Partly present: Streamlit history versus learner-keyed SQLite. No explicit graph thread IDs/checkpointer. | UUID thread IDs and `InMemorySaver`; approved user records remain in SQLite across threads. |
| At least 2 stored and retrieved memory records | Multiple SQL data types exist, but exact required scenario evidence is absent. | Separate style and level records, visibly loaded by later threads; tests and simulation evidence. |
| New thread uses an earlier record | Reuse is supported by `student_id`; no submission-ready proof found. | New-thread button, CLI scenarios, source-thread metadata and prompt-level assertions. |
| Memory influences later output | Learner level/weaknesses influence prompts. Stored `preferred_style` does not. | Both saved format and level are passed to the tutor prompt. Offline simulation demonstrates the change. |
| Memory update/correction | Weak/strong topic update helpers exist, but no explicit preference-correction path or focused evidence. | Reviewed preference correction updates the same key and increments its revision; a later thread uses the corrected format. |
| Why information is retained; risky/irrelevant handling | No clear retention policy found. | Fixed learning-related keys/values; no arbitrary conversation-to-memory extraction; policy in README/report. |
| Normal, later-memory and rejection scenarios | `quick_test.py` checks imports/components, not these end-to-end cases. | New scenario suite, interactive demo, labeled simulation evidence and expected-behavior guide. |
| Runnable code, dependencies and setup | README and unpinned requirements exist; clients initialize at import and require credentials even for unrelated checks. | Lazy provider client, pinned Project 1 dependencies, `.env.example`, offline tests and fresh local DB. |
| Architecture diagram | `eduagentsys.png` exists but could not be decoded as PNG in this checkout. | New renderable Mermaid architecture explicitly includes state, memory, source tool, LLM and approval. |
| Test evidence and limitations | Component test script exists; no Project 1 scenario results found. | Recorded passing tests and simulated run, with live-LLM and prototype limitations identified. |
| 1–2 page report and individual contributions | Not found in the baseline tree. | Short report draft added. Team contributions and final formatting require the team's input. |
| Authorized/sample data; no submitted keys | `.env`/credentials were not tracked in the inspected tree. Notes and a historical demo DB are bundled; their origin is not independently established. | Git ignore rules and fresh local/demo databases added. Use only materials the team is permitted to process. |
| Team size 1–3, instructor confirmation | Not established by repository files. | Remains a team/instructor action; cannot be inferred or fabricated. |
| Live demo with inputs/outputs and edge/rejection case | Not established by repository files. | Repeat `python demo_project1.py` with the real provider and interactive decisions; attach that evidence before submission. |

## Additional concrete defects addressed

- Quiz correctness compared only the first 15 characters of answer text. Different answers sharing that prefix could receive the same grade. It now compares complete normalized options.
- Starting a new session cleared chat but did not clear the active quiz. The new thread reset clears quiz, pending approval and request state.
- Quiz evaluation and explanation functions wrote learning memory immediately. The application now prepares changes and commits them after review.
- Malformed quiz JSON was parsed without verifying question structure. The generator now checks count, options, answer membership and explanations.
- The model-assisted safety check accepted unknown output and failed open on provider errors. It now declines to proceed when it cannot validate the request.

## Scope judgment

The baseline is a useful foundation but is not fully compliant with Project 1: human approval/rejection and convincing memory/correction evidence are the largest gaps. The revised implementation supplies those paths and offline evidence. It is not yet a complete submission until live LLM behavior, a human demonstration, report details and team contributions are supplied.

Do not treat SQLite, a UI, or helper files named “agent” as proof of Project 2 compliance. Shared memory, agent collaboration, sharing controls and their evidence need a separate review later.
