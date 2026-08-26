"""Productivity Sub-Agent — File Analysis & Organizer."""
import os
import shutil
import mimetypes
from pathlib import Path
from typing import Dict, List
from datetime import datetime

from utils.llm_config import get_kimi_client
from langchain_core.messages import HumanMessage

BASE_DIR = Path(__file__).parent.parent
RAW_DIR = BASE_DIR / "data" / "raw_files"
SORTED_DIR = BASE_DIR / "data" / "sorted_files"

CATEGORY_MAP = {
    "Code": [".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".scss", ".java", ".cpp", ".c", ".h", ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".sql", ".json", ".xml", ".yaml", ".yml", ".sh", ".bat", ".ps1"],
    "Documents": [".pdf", ".doc", ".docx", ".txt", ".md", ".rtf", ".odt", ".tex", ".epub"],
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".ico", ".tiff"],
    "Archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"],
    "Data": [".csv", ".xls", ".xlsx", ".db", ".sqlite", ".parquet"],
    "Media": [".mp3", ".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".wav", ".aac", ".flac"],
    "Others": [],
}


def categorize_file(file_path: Path) -> str:
    """Categorize a file based on its extension."""
    ext = file_path.suffix.lower()
    for category, extensions in CATEGORY_MAP.items():
        if ext in extensions:
            return category
    return "Others"


def analyze_files() -> List[Dict]:
    """Scan raw_files directory and analyze all files."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    SORTED_DIR.mkdir(parents=True, exist_ok=True)
    files_info = []
    for file_path in RAW_DIR.iterdir():
        if file_path.is_file():
            stat = file_path.stat()
            category = categorize_file(file_path)
            mime, _ = mimetypes.guess_type(str(file_path))
            files_info.append({
                "name": file_path.name,
                "path": str(file_path),
                "size": stat.st_size,
                "size_human": f"{stat.st_size / 1024:.1f} KB" if stat.st_size < 1024*1024 else f"{stat.st_size / (1024*1024):.2f} MB",
                "category": category,
                "mime": mime or "unknown",
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
            })
    return files_info


def organize_files(files_info: List[Dict], dry_run: bool = False) -> Dict:
    """Move files to sorted directories."""
    logs = []
    moved = 0
    skipped = 0
    for info in files_info:
        src = Path(info["path"])
        dest_dir = SORTED_DIR / info["category"]
        dest_dir.mkdir(exist_ok=True)
        dest = dest_dir / info["name"]
        if dest.exists():
            logs.append(f"SKIP: {info['name']} already exists in {info['category']}/")
            skipped += 1
            continue
        if not dry_run:
            try:
                shutil.move(str(src), str(dest))
                logs.append(f"MOVED: {info['name']} -> {info['category']}/")
                moved += 1
            except Exception as e:
                logs.append(f"ERROR: {info['name']} — {str(e)}")
                skipped += 1
        else:
            logs.append(f"PREVIEW: {info['name']} -> {info['category']}/")
            moved += 1
    return {
        "moved": moved,
        "skipped": skipped,
        "logs": logs,
        "categories": list(set(f["category"] for f in files_info)),
    }


def generate_summary_with_llm(files_info: List[Dict]) -> str:
    """Use Kimi to generate a smart summary of the file batch."""
    if not files_info:
        return "No files found in raw_files directory."
    try:
        client = get_kimi_client(temperature=0.3, max_tokens=512)
        lines = []
        lines.append(f"Files found: {len(files_info)}")
        for f in files_info[:20]:
            lines.append(f"- {f['name']} ({f['category']}, {f['size_human']})")
        if len(files_info) > 20:
            lines.append(f"... and {len(files_info) - 20} more files.")
        summary = "\n".join(lines)
        prompt = f"""As a Productivity Agent, analyze this file batch and provide:
1. A brief overview of what types of files dominate
2. Any organization recommendations
3. A witty one-liner about the user's digital habits

Files:
{summary}
"""
        response = client.invoke([HumanMessage(content=prompt)])
        return response.content
    except Exception as e:
        return f"File analysis complete. {len(files_info)} files detected. (LLM summary unavailable: {e})"


def run_productivity_agent(user_input: str, context: dict) -> dict:
    """Main entry for productivity tasks."""
    user_lower = user_input.lower()
    dry_run = "preview" in user_lower or "dry run" in user_lower or "show" in user_lower
    files_info = analyze_files()
    if not files_info:
        return {
            "response": "The data/raw_files/ directory is empty. Drop some files there and I will organize them!",
            "files": [],
            "organization": None,
            "summary": "No files to process.",
        }
    org_result = organize_files(files_info, dry_run=dry_run)
    summary = generate_summary_with_llm(files_info)
    action_word = "Previewed" if dry_run else "Organized"
    log_lines = "\n".join(org_result['logs'][:10])
    more_text = "... and more entries" if len(org_result['logs']) > 10 else ""
    response = f"""## Productivity Agent Report

**{action_word}** `{len(files_info)}` files across `{len(org_result['categories'])}` categories.

| Metric | Count |
|--------|-------|
| Moved | {org_result['moved']} |
| Skipped | {org_result['skipped']} |

### Agent Insight
{summary}

### Execution Log
```
{log_lines}
```
{more_text}
"""
    return {
        "response": response,
        "files": files_info,
        "organization": org_result,
        "summary": summary,
    }