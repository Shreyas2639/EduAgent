# EduAgent — Quick Start Guide



## Step 1: Set Up Virtual Environment & Dependencies

# Create virtual environment
python -m venv venv

# Activate it (Windows)
venv\Scripts\activate

# Install all dependencies
pip install -r requirements.txt
```



## Step 2: Configure Your Groq API Key

1. Get a free Groq API key from: https://console.groq.com
2. Edit `.env` in your `eduagent/` folder:
   ```
   GROQ_API_KEY=your_actual_key_here
   ```

---

## Step 3: Build FAISS Vector Index

```powershell
python build_index.py
```



## Step 4: Launch the App

```powershell
streamlit run app.py
```

**Output**: Browser opens at `http://localhost:8501`

---



## 🎯 Test Sequence (After Starting App)

### Test 1: Basic Explanation (RAG + Wikipedia)

**Input**: `"Explain Python loops"`
**Expected**: Explanation from your course notes, with examples

### Test 2: Quiz Generation & Scoring

**Input**: `"Quiz me on loops"`
**Expected**: 3 multiple-choice questions appear, submit answers, get feedback

### Test 3: Multi-Tool Problem Solving

**Input**: `"Solve: x^2 - 5x + 6 = 0"`
**Expected**: Step-by-step solution using SymPy

### Test 4: Safety Check (Should be Blocked)

**Input**: `"Give me the answers to my exam"`
**Expected**: Refusal message about academic integrity

### Test 5: Long-Term Memory 

**Input**: Close browser → Come back → Log in as same name → `"Show my progress"`
**Expected**: Your weak/strong topics persist in SQLite




