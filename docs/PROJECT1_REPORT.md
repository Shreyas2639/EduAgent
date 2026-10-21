# EduAgent: Memory-enabled Python tutor

**Project 1 report draft — finalize team details and live results before submission.**

## Problem and goal

A learner should be able to ask for Python Fundamentals explanations and practice quizzes without repeating their preferred learning format and level in every new conversation. EduAgent accepts a learner identity, a study request and optional preference changes. It returns a course-note-grounded explanation, a practice quiz or a progress summary, together with a reviewable proposal when reusable learning memory should change.

## Design and implementation

The application uses Python, LangGraph, Groq and SQLite. It is one logical tutoring agent; helper functions perform intent classification, topic resolution, tutoring and feedback. The workflow loads learner memory, checks the request, selects a route, retrieves permitted local notes, and generates a result. Preferences can also be changed through structured controls. A notebook or CLI would be sufficient; Streamlit provides a convenient existing interface.

Thread state contains the current request, recent conversation, retrieved sources, current quiz and pending approval. A UUID and an in-memory checkpoint identify each conversation. SQLite stores reusable memory under a stable simulated learner identity. These are separate boundaries: a new thread starts with empty chat while retrieving the same learner's approved records.

The memory table holds separate `preferred_style`, `level` and `last_topic` records with revision and source-thread metadata. The tutor prompt uses the saved format and level. Correcting a preference updates its existing key and increments its revision. A deterministic note-retrieval tool reads the bundled curriculum; vector search is not needed for this milestone.

## Human control and retention

The application shows proposed memory changes and their previous values, pauses through a LangGraph interrupt, and requires an explicit boolean approval. Approval commits the reviewed changes; rejection keeps the current answer and leaves reusable learning records unchanged. Quiz grading similarly prepares results before asking to retain progress. Defaults/account registration are setup operations rather than inferred learning memories.

Learning preferences and recent course progress are useful because they can improve a later explanation or recommendation. The system accepts only fixed learning-related keys and values, rather than retaining arbitrary chat, unrelated details or credentials. Course-note excerpts and relevant prompts are sent to Groq, so demonstrations must use authorized sample data.

## Tests and current results

The automated suite verifies real graph execution, local-note retrieval, SQLite records, new-thread reuse, preference correction, rejection, invalid approval values and UI controls. It also checks malformed quiz handling, missing notes, quiz ownership across threads and complete-answer grading. Recorded results and a seven-scenario simulation are included separately. Model responses are simulated in these tests; this establishes control flow and memory behavior, not live answer quality.

**Live demonstration results:** pending a run with the team's Groq key and interactive decisions. Replace this paragraph with actual outcomes and reference the saved evidence. Do not describe the simulation as a successful live model run.

## Limitations and next steps

Simulated learner names are not authenticated accounts. Checkpoints disappear on restart, while approved SQLite memory persists. Keyword retrieval supports a small curriculum and can miss relevant notes. Model output can be incorrect despite structural checks, and the safety classifier can overblock requests. This milestone does not implement multi-agent collaboration or shared memory. Later milestones should extend the same tutor with specialized collaborating agents, explicit sharing controls and more failure tests.

## Individual contributions

**Complete before submission:** list each actual team member, implemented components, testing/documentation work and any AI assistance according to course expectations. Contributions and instructor confirmation cannot be established from the repository audit.
