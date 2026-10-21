# EduAgent — Project 1

EduAgent helps a simulated learner study Python Fundamentals using bundled course notes, explanations, practice quizzes, and reusable learning preferences. It is one logical LLM-powered tutor implemented as a stateful LangGraph workflow. Helper modules named `agents` provide functions for that tutor; this milestone does not claim multi-agent collaboration.

The Project 1 path adds a genuine approval pause before saving substantive learning memory. A learner can inspect a proposed change, approve or reject it, correct a preference, and start a new conversation thread that reuses approved records.

## Run

Use Python 3.12 and a virtual environment from the repository root:

```bash
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell instead:
# .venv\Scripts\Activate.ps1
python -m pip install -r requirements-project1.txt
```

Copy `.env.example` to `.env` and set your own `GROQ_API_KEY`. The model defaults to `llama-3.3-70b-versatile`; set `GROQ_MODEL` if your Groq account requires another available model. Never commit `.env`.

```bash
python -m streamlit run app.py
```

Enter a **simulated** learner name. Set the preferred format and level, click **Review memory changes**, then approve. Ask `Explain Python loops`. Review the proposed last-topic record. Use **New thread — keep approved memory** and ask `Explain Python functions`. Inspect the saved records, then correct a preference or reject a change.

The application sends relevant prompts, learning preferences, and course-note excerpts to Groq. SQLite files remain local. Use authorized sample data. Name-based demo identities are not authentication.

## Project 1 demonstration

```bash
python demo_project1.py
```

This uses a real Groq LLM and asks for each approval interactively. It demonstrates a baseline, two saved preference records, a normal request, a new thread using memory, a correction, a later request after correction, and rejection. Follow the rejection instruction at the final prompt. Each run creates a fresh directory under `demo_runs/` and saves `evidence.json`; previous runs are retained.

For offline development only:

```bash
python demo_project1.py --simulate
# Explicitly scripted simulation for automated verification only:
python demo_project1.py --simulate --scripted
python -m pytest -q
```

Simulation replaces provider responses with a deterministic fake. It uses the real graph, note-retrieval tool, SQLite memory, and approval branches. It does **not** prove live LLM integration or replace a human approval demonstration. Live mode never scripts decisions.

## State and memory boundaries

- `AgentState`, `ShortTermMemory`, and `InMemorySaver` hold the current request, conversation, quiz, sources, pending proposal, and approval checkpoint. A UUID identifies each UI thread.
- SQLite is an equivalent cross-thread user-memory backend. `user_memories` contains separate `(student_id, memory_key)` records for `preferred_style`, `level`, and `last_topic`, including revisions and source-thread IDs.
- The tutor prompt actually uses approved style and level. A correction updates the existing record rather than accumulating conflicting values.
- Explicit preferences and valid course progress are useful for later tutoring. Arbitrary messages, credentials, unrelated facts, and inferred personal details are not reusable-memory candidates. Only fixed preference values and curriculum topics are accepted.
- The current application writes proposed preferences, last studied topic, and quiz progress only after approval. Rejecting preserves the answer but changes no reusable learning record. Account registration/defaults and database schema initialization are separate setup operations.
- `database/eduagent_local.db` is created automatically and ignored by Git. Set `EDUAGENT_DB_PATH` to use another path. The historical tracked `database/eduagent.db` is not the default data source.
- Checkpoints are in RAM. Restarting the app loses paused conversations; approved SQLite records survive. Restart-safe checkpoints are not required for Project 1.

## Information source and optional older tools

The Project 1 workflow explicitly retrieves relevant bundled `.txt` notes using a small keyword-based tool in `rag/local_retriever.py`. Missing sources produce an honest response instead of invented course notes. No embedding download or prebuilt index is needed for this path.

The earlier FAISS index builder, vector retriever, Wikipedia tool, and broad `requirements.txt` remain for experimentation. They are not necessary to run or verify the Project 1 path. SymPy remains a helper for course-related problem solving. The older `quick_test.py` checks optional components; use the new `tests/` suite for Project 1 acceptance checks.

## Documentation and evidence

- [Requirement audit: original repository versus this change](docs/PROJECT1_AUDIT.md)
- [Architecture and state boundaries](docs/PROJECT1_ARCHITECTURE.md)
- [Demo steps and expected results](docs/PROJECT1_DEMO.md)
- [Short report draft](docs/PROJECT1_REPORT.md)
- [Recorded automated test results](docs/project1_test_results.txt)
- [Labeled simulation evidence](docs/project1_simulation_evidence.json)

**Submission still requires:** a live run with a valid LLM key, actual demonstration evidence, confirmed team size and truthful individual contributions, and a finalized 1–2 page report. No course-grade prediction is made from offline tests.
