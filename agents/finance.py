"""Finance Sub-Agent — Expense Analysis & Budget Advisor."""
import os
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd

from utils.llm_config import get_kimi_client
from langchain_core.messages import HumanMessage

BASE_DIR = Path(__file__).parent.parent
FINANCE_DIR = BASE_DIR / "data" / "financial_docs"

CATEGORY_KEYWORDS = {
    "Groceries": ["grocery", "supermarket", "walmart", "target", "kroger", "safeway", "whole foods", "trader joe", "aldi", "food", "market"],
    "Rent/Housing": ["rent", "apartment", "housing", "mortgage", "lease", "property", "realty"],
    "Utilities": ["electric", "gas", "water", "sewer", "utility", "power", "energy", "internet", "wifi", "broadband", "phone bill", "cellular"],
    "Entertainment": ["netflix", "spotify", "hulu", "disney", "amazon prime", "youtube", "movie", "theater", "cinema", "concert", "game", "entertainment", "streaming"],
    "Dining Out": ["restaurant", "cafe", "coffee", "starbucks", "mcdonalds", "burger", "pizza", "sushi", "doordash", "uber eats", "grubhub", "delivery"],
    "Transportation": ["uber", "lyft", "taxi", "gas station", "shell", "bp", "exxon", "transit", "bus", "train", "subway", "parking", "toll"],
    "Shopping": ["amazon", "ebay", "etsy", "shop", "store", "mall", "retail", "clothing", "fashion", "electronics"],
    "Health": ["pharmacy", "hospital", "clinic", "doctor", "dental", "medical", "health", "insurance", "gym", "fitness"],
    "Education": ["tuition", "book", "course", "class", "university", "college", "school", "education", "learning", "udemy", "coursera"],
    "Travel": ["airline", "hotel", "booking", "airbnb", "expedia", "flight", "travel", "vacation", "trip"],
    "Income": ["salary", "paycheck", "deposit", "refund", "interest", "dividend", "wage", "payment received"],
}


def categorize_transaction(description: str, amount: float) -> str:
    """Categorize a transaction based on description keywords."""
    desc_lower = description.lower()
    if amount > 0:
        for cat, keywords in CATEGORY_KEYWORDS.items():
            if cat == "Income":
                for kw in keywords:
                    if kw in desc_lower:
                        return cat
        return "Income"
    for category, keywords in CATEGORY_KEYWORDS.items():
        if category == "Income":
            continue
        for kw in keywords:
            if kw in desc_lower:
                return category
    return "Uncategorized"


def parse_bank_statement(file_path: Path) -> Optional[pd.DataFrame]:
    """Parse a CSV or Excel bank statement."""
    try:
        if file_path.suffix.lower() == ".csv":
            df = pd.read_csv(file_path)
        elif file_path.suffix.lower() in [".xls", ".xlsx"]:
            df = pd.read_excel(file_path)
        else:
            return None
        df.columns = [c.strip().lower() for c in df.columns]
        date_col = next((c for c in df.columns if any(k in c for k in ["date", "time", "day"])), None)
        desc_col = next((c for c in df.columns if any(k in c for k in ["description", "desc", "memo", "payee", "transaction", "details", "merchant"])), None)
        amount_col = next((c for c in df.columns if any(k in c for k in ["amount", "sum", "value", "price", "total"])), None)
        if not all([date_col, desc_col, amount_col]):
            return None
        df = df.rename(columns={date_col: "date", desc_col: "description", amount_col: "amount"})
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        df = df.dropna(subset=["amount", "description"])
        df["category"] = df.apply(lambda row: categorize_transaction(row["description"], row["amount"]), axis=1)
        return df
    except Exception as e:
        print(f"Parse error: {e}")
        return None


def analyze_spending(df: pd.DataFrame) -> Dict:
    """Analyze spending patterns and generate metrics."""
    expenses = df[df["amount"] < 0].copy()
    expenses["amount"] = expenses["amount"].abs()
    income = df[df["amount"] > 0]["amount"].sum()
    total_spent = expenses["amount"].sum()
    by_category = expenses.groupby("category")["amount"].agg(["sum", "count"]).reset_index()
    by_category.columns = ["category", "total", "count"]
    by_category = by_category.sort_values("total", ascending=False)
    by_category["percentage"] = (by_category["total"] / total_spent * 100).round(1)
    monthly_trend = None
    if "date" in df.columns:
        try:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            monthly = df[df["amount"] < 0].copy()
            monthly["amount"] = monthly["amount"].abs()
            monthly["month"] = monthly["date"].dt.to_period("M")
            monthly_trend = monthly.groupby("month")["amount"].sum().to_dict()
        except:
            pass
    return {
        "total_income": income,
        "total_expenses": total_spent,
        "net": income - total_spent,
        "transaction_count": len(df),
        "expense_count": len(expenses),
        "by_category": by_category.to_dict("records"),
        "monthly_trend": monthly_trend,
        "top_merchant": expenses.groupby("description")["amount"].sum().idxmax() if len(expenses) > 0 else "N/A",
    }


def generate_budget_advice(metrics: Dict) -> str:
    """Use Kimi to generate personalized budget advice."""
    try:
        client = get_kimi_client(temperature=0.4, max_tokens=1024)
        cat_summary = "\n".join([
            f"- {c['category']}: ${c['total']:.2f} ({c['percentage']}%, {c['count']} transactions)"
            for c in metrics["by_category"][:8]
        ])
        prompt = f"""You are a Financial Advisor Agent. Analyze this spending report and provide actionable budget advice.

Financial Snapshot:
- Total Income: ${metrics['total_income']:.2f}
- Total Expenses: ${metrics['total_expenses']:.2f}
- Net: ${metrics['net']:.2f}
- Top Merchant: {metrics['top_merchant']}

Spending Breakdown:
{cat_summary}

Provide:
1. A financial health score (0-100) with reasoning
2. Top 3 areas to reduce spending
3. Specific savings recommendations
4. A 50/30/20 budget rule assessment
5. One encouraging remark

Format with Markdown headings."""
        response = client.invoke([HumanMessage(content=prompt)])
        return response.content
    except Exception as e:
        return f"Budget analysis complete. Net savings: ${metrics['net']:.2f}. (LLM advice unavailable: {e})"


def run_finance_agent(user_input: str, context: dict) -> dict:
    """Main entry for finance tasks."""
    FINANCE_DIR.mkdir(parents=True, exist_ok=True)
    statements = list(FINANCE_DIR.glob("*.csv")) + list(FINANCE_DIR.glob("*.xlsx")) + list(FINANCE_DIR.glob("*.xls"))
    if not statements:
        return {
            "response": "No bank statements found in data/financial_docs/. Please upload a CSV or Excel file!",
            "metrics": None,
            "advice": None,
        }
    target_file = max(statements, key=lambda p: p.stat().st_mtime)
    for stmt in statements:
        if stmt.name.lower() in user_input.lower():
            target_file = stmt
            break
    df = parse_bank_statement(target_file)
    if df is None:
        return {
            "response": f"Could not parse {target_file.name}. Ensure it has Date, Description, and Amount columns.",
            "metrics": None,
            "advice": None,
        }
    metrics = analyze_spending(df)
    advice = generate_budget_advice(metrics)
    lines = []
    lines.append("## Finance Agent Report")
    lines.append("")
    lines.append(f"**File:** `{target_file.name}` | **Transactions:** {metrics['transaction_count']}")
    lines.append("")
    lines.append("### Key Metrics")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Total Income | ${metrics['total_income']:.2f} |")
    lines.append(f"| Total Expenses | ${metrics['total_expenses']:.2f} |")
    lines.append(f"| Net Flow | ${metrics['net']:.2f} |")
    lines.append(f"| Top Merchant | {metrics['top_merchant']} |")
    lines.append("")
    lines.append("### Spending Breakdown")
    lines.append("| Category | Amount | % | Count |")
    lines.append("|----------|--------|---|-------|")
    for c in metrics["by_category"][:10]:
        lines.append(f"| {c['category']} | ${c['total']:.2f} | {c['percentage']}% | {c['count']} |")
    lines.append("")
    lines.append("### Advisor Insight")
    lines.append(advice)
    response = "\n".join(lines)
    return {
        "response": response,
        "metrics": metrics,
        "advice": advice,
        "dataframe": df,
    }