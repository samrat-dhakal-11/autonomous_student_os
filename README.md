# 🎓 The Autonomous Student OS

A production-grade, multi-agent command center for students powered by **GROQ** and orchestrated via **LangGraph**.

## 🏛️ Architecture

- **Orchestration:** LangGraph (StateGraph with conditional routing)
- **LLM Engine:** GROQ API (OpenAI-compatible endpoint)
- **Dashboard:** Streamlit + Glassmorphism CSS
- **Storage:** Local filesystem + ChromaDB (optional vector store)

## 📦 Installation

```bash
cd the_autonomous_student_os/autonomous_student_os
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your KIMI_API_KEY
```

## 🚀 Run

```bash
streamlit run app.py
```

## 📂 Project Structure

```
autonomous_student_os/
├── app.py                  # Main Streamlit dashboard
├── requirements.txt
├── .env.example
├── README.md
├── agents/                 # Multi-Agent Logic
│   ├── master_router.py
│   ├── productivity.py
│   ├── academics.py
│   ├── finance.py
│   └── career.py
├── utils/
│   ├── llm_config.py
│   └── vector_store.py
└── data/
    ├── raw_files/
    ├── sorted_files/
    ├── academic_docs/
    └── financial_docs/
```

## 🧠 Agents

| Agent | Domain | Capabilities |
|-------|--------|-------------|
| **Master Router** | Orchestration | Intent classification, dynamic routing |
| **Productivity** | Files | Auto-categorize, move, and organize files |
| **Academics** | Learning | Code debugger, PDF summarizer & Q&A |
| **Finance** | Money | CSV parser, expense categorization, budget advice |
| **Career** | Jobs | Mock interviewer with dynamic scoring |

## 🎨 UI Features

- Glassmorphism cards with gradient accents
- Real-time agent execution logs
- Interactive charts and metrics
- Responsive sidebar navigation
