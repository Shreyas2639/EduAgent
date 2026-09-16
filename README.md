# EduAgent

EduAgent is a personalized AI tutor I built to explore how agentic AI can support learning instead of simply answering questions. It can explain Python concepts, create quizzes, evaluate answers, solve symbolic math problems, remember a learner's progress, and recommend what to study next.

My goal was to combine several useful AI patterns in one practical application: explicit agent routing with LangGraph, retrieval-augmented generation over private course notes, deterministic tools for tasks such as algebra, and persistent learner memory with SQLite.

## What EduAgent Can Do

- Explain concepts using locally stored course notes as the primary source
- Generate three-question multiple-choice quizzes on requested topics
- Evaluate quiz answers and provide personalized feedback
- Track strong, weak, and completed topics across sessions
- Recommend the next topic using a prerequisite-based course map
- Solve symbolic math expressions with SymPy
- Retrieve external background information from Wikipedia when local notes are insufficient
- Block requests that involve academic cheating or harmful assistance

## How It Works

Every message first passes through a safety check. Safe requests are sent to a coordinator that uses the Groq LLM to classify the request as one of six intents:

- `EXPLAIN`
- `QUIZ`
- `SOLVE`
- `FEEDBACK`
- `MEMORY`
- `GENERAL`

LangGraph then routes the request to the appropriate workflow node. Explanation and quiz requests can retrieve relevant content from the FAISS index. Math requests can use SymPy, and explanation requests can fall back to Wikipedia when the local course notes do not contain relevant information.

The Streamlit interface manages the conversation and interactive quiz form. Quiz results are evaluated and written to SQLite so that progress remains available after the browser is refreshed or a new session begins.

## Technology Stack

- Python
- Streamlit
- LangGraph
- Groq with Llama 3.3 70B
- FAISS
- Sentence Transformers
- SQLite
- SymPy
- Wikipedia API
- LangChain text splitters

## Project Structure

```text
eduagent/
|-- agents/              # Intent classification, tutoring, quizzes, and feedback
|-- database/            # SQLite database used for persistent learner memory
|-- graph/               # LangGraph workflow and routing
|-- knowledge_base/
|   |-- notes/           # Local Python course material
|   `-- quiz_bank/       # Sample quiz content
|-- memory/              # Short-term conversation and long-term learner memory
|-- rag/                 # Document loading, embeddings, indexing, and retrieval
|-- safety/              # Rule-based and LLM-assisted safety checks
|-- tools/               # SymPy and Wikipedia integrations
|-- vector_store/        # Persisted FAISS index and document metadata
|-- app.py               # Streamlit application
|-- build_index.py       # Rebuilds the FAISS knowledge index
|-- course_map.py        # Course topics, prerequisites, and recommendations
|-- quick_test.py        # Basic validation tests
`-- requirements.txt     # Python dependencies
```

## Learner Memory

EduAgent uses two forms of memory:

1. Short-term memory keeps recent conversation messages available during the current Streamlit session.
2. Long-term memory stores learner information in `database/eduagent.db`.

The SQLite database contains student profiles, strong and weak topics, completed topics, recent quiz attempts, and session summaries. The database included in this repository contains demonstration data used while testing the application.

## Getting Started

### 1. Create a virtual environment

```powershell
python -m venv venv
venv\Scripts\activate
```

### 2. Install the dependencies

```powershell
pip install -r requirements.txt
```

### 3. Configure the Groq API key

Create a `.env` file in the project directory:

```env
GROQ_API_KEY=your_groq_api_key
```

You can create a Groq API key at [console.groq.com](https://console.groq.com/).

### 4. Build the knowledge index

The repository already contains a generated FAISS index. Run this command if you change the course notes or want to rebuild it:

```powershell
python build_index.py
```

### 5. Start EduAgent

```powershell
streamlit run app.py
```

Streamlit will provide a local URL, normally `http://localhost:8501`.

## Example Prompts

```text
Explain Python loops
Quiz me on recursion
Solve: x^2 - 5x + 6 = 0
Show my progress
What should I study next?
```

## Testing

Run the included validation script with:

```powershell
python quick_test.py
```

The test runner checks core imports, database initialization, the safety guard, short-term memory, Wikipedia retrieval, and SymPy integration. Some checks require internet access and a valid Groq API key.

## Current Scope

EduAgent currently focuses on a Python Fundamentals curriculum. Learners are identified by a normalized version of the name entered in the Streamlit sidebar, so this version is intended as an educational prototype rather than a production learning platform.

I see this project as a foundation for experimenting with adaptive difficulty, broader course support, stronger authentication, richer evaluation, and more detailed learning analytics.

