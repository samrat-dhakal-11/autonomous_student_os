"""Academics Sub-Agent — Code Debugger & PDF Reader/Summarizer."""
import os
import re
from pathlib import Path
from typing import Dict, List, Optional
from pypdf import PdfReader

from utils.llm_config import get_kimi_client
from langchain_core.messages import HumanMessage

BASE_DIR = Path(__file__).parent.parent
ACADEMIC_DIR = BASE_DIR / "data" / "academic_docs"


def extract_pdf_text(pdf_path: Path, max_pages: int = 50) -> str:
    """Extract text from a PDF file."""
    try:
        reader = PdfReader(str(pdf_path))
        text = ""
        for i, page in enumerate(reader.pages[:max_pages]):
            text += page.extract_text() or ""
            if len(text) > 120000:
                break
        return text
    except Exception as e:
        return f"[PDF Error: {e}]"


def list_academic_pdfs() -> List[Dict]:
    """List all PDFs in the academic_docs directory."""
    ACADEMIC_DIR.mkdir(parents=True, exist_ok=True)
    pdfs = []
    for f in ACADEMIC_DIR.glob("*.pdf"):
        stat = f.stat()
        pdfs.append({
            "name": f.name,
            "path": str(f),
            "size": f"{stat.st_size / 1024:.1f} KB",
        })
    return pdfs


def debug_code(code_snippet: str, language: str = "python") -> str:
    """Analyze code for bugs and suggest fixes."""
    client = get_kimi_client(temperature=0.2, max_tokens=2048)
    prompt = f"""You are an expert Code Debugger Agent. Analyze the following {language} code:

1. Identify bugs, errors, or anti-patterns
2. Explain the root cause of each issue
3. Provide a corrected version of the code
4. Generate brief Markdown documentation for the fixed function

Format your response with:
- ## Issues Found
- ## Corrected Code
- ## Documentation

Code:
```{language}
{code_snippet}
```
"""
    response = client.invoke([HumanMessage(content=prompt)])
    return response.content


def summarize_pdf(pdf_path: Path, query: Optional[str] = None) -> str:
    """Summarize a PDF or answer questions about it."""
    text = extract_pdf_text(pdf_path)
    if text.startswith("[PDF Error"):
        return text
    if not text.strip():
        return "Could not extract text from this PDF. It may be scanned/image-based."
    max_chars = 100000
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[Document truncated due to length...]"
    client = get_kimi_client(temperature=0.3, max_tokens=2048)
    if query:
        prompt = f"""You are an Academic Research Assistant. Based on the following document, answer the user's question comprehensively.

Document:
{text[:80000]}

Question: {query}

Provide a detailed, well-structured answer with citations from the text where possible."""
    else:
        prompt = f"""You are an Academic Summarizer Agent. Provide a comprehensive summary of the following research paper/document:

{text[:80000]}

Include:
1. Main objective / research question
2. Key methodology
3. Primary findings / results
4. Conclusions and implications
5. Suggested further reading topics

Format with clear Markdown headings."""
    response = client.invoke([HumanMessage(content=prompt)])
    return response.content


def run_academics_agent(user_input: str, context: dict) -> dict:
    """Main entry for academic tasks."""
    user_lower = user_input.lower()
    code_pattern = re.compile(r"```(?:\w+)?\n(.*?)\n```", re.DOTALL)
    code_match = code_pattern.search(user_input)
    pdfs = list_academic_pdfs()
    pdf_names = [p["name"] for p in pdfs]
    mentioned_pdf = None
    for pdf in pdf_names:
        if pdf.lower() in user_lower:
            mentioned_pdf = pdf
            break
    if code_match or any(kw in user_lower for kw in ["bug", "debug", "fix", "error", "code", "function", "class", "syntax"]):
        code = code_match.group(1) if code_match else user_input
        lang = "python"
        if "javascript" in user_lower or "js" in user_lower:
            lang = "javascript"
        elif "java" in user_lower:
            lang = "java"
        elif "cpp" in user_lower or "c++" in user_lower:
            lang = "cpp"
        result = debug_code(code, lang)
        return {"response": result, "task": "code_debug", "language": lang}
    elif mentioned_pdf or any(kw in user_lower for kw in ["pdf", "paper", "research", "document", "summarize", "read"]):
        if not pdfs:
            return {
                "response": "No PDFs found in data/academic_docs/. Please upload a research paper first!",
                "task": "pdf_analysis",
                "pdfs": [],
            }
        target_pdf = mentioned_pdf or pdfs[0]["name"]
        pdf_path = ACADEMIC_DIR / target_pdf
        query = None
        if "question" in user_lower or "what is" in user_lower or "how does" in user_lower or "explain" in user_lower:
            query = user_input
        result = summarize_pdf(pdf_path, query)
        return {
            "response": f"## Academic Agent: {target_pdf}\n\n{result}",
            "task": "pdf_analysis",
            "pdf": target_pdf,
            "query": query,
        }
    else:
        client = get_kimi_client(temperature=0.5, max_tokens=1024)
        prompt = f"""You are a knowledgeable Academic Tutor. Help the student with their question.

Student: {user_input}

Provide a clear, structured explanation with examples where helpful."""
        response = client.invoke([HumanMessage(content=prompt)])
        return {"response": response.content, "task": "general_academic"}