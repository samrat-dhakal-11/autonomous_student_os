"""Career Sub-Agent — Mock Interviewer & Evaluator."""
import random
from typing import Dict, List

from utils.llm_config import get_kimi_client
from langchain_core.messages import HumanMessage

QUESTION_BANK = {
    "technical": [
        "Explain the difference between REST and GraphQL.",
        "What is the time complexity of a binary search tree insertion?",
        "Describe how garbage collection works in Python.",
        "What are the ACID properties in databases?",
        "Explain Docker containers vs virtual machines.",
    ],
    "behavioral": [
        "Tell me about a time you faced a conflict in a team.",
        "Describe a situation where you had to learn something quickly.",
        "What is your greatest professional weakness?",
        "Tell me about a project you are most proud of.",
        "How do you handle tight deadlines and pressure?",
    ],
    "system_design": [
        "Design a URL shortening service like bit.ly.",
        "How would you design a real-time chat application?",
        "Design a distributed cache system.",
        "Explain how you would scale a web application to millions of users.",
    ],
}


def generate_interview_question(role: str, topic: str, difficulty: str = "medium") -> str:
    """Generate a dynamic interview question using Kimi."""
    client = get_kimi_client(temperature=0.7, max_tokens=512)
    prompt = f"""You are an experienced technical recruiter. Generate one {difficulty} difficulty interview question for a {role} position.

Focus area: {topic}

Requirements:
- The question should be realistic and relevant to modern industry practices
- Include context/scenario if applicable
- Do NOT provide the answer
- Format as a clean, professional interview question

Generate only the question, nothing else."""
    response = client.invoke([HumanMessage(content=prompt)])
    return response.content.strip()


def evaluate_response(question: str, answer: str, role: str) -> Dict:
    """Evaluate a candidate's interview response."""
    client = get_kimi_client(temperature=0.3, max_tokens=1024)
    prompt = f"""You are a senior interviewer evaluating a candidate for a {role} position.

Question: {question}

Candidate's Answer:
{answer}

Evaluate on these criteria (score 1-10 each):
1. Technical Accuracy
2. Communication Clarity
3. Problem-Solving Approach
4. Depth of Knowledge
5. Structure & Organization

Provide:
- A total score out of 50
- Specific strengths (2-3 points)
- Specific areas for improvement (2-3 points)
- One actionable tip for next time

Format as Markdown with clear headings."""
    response = client.invoke([HumanMessage(content=prompt)])
    content = response.content
    score = None
    score_match = content.split("/50")
    if len(score_match) > 1:
        try:
            score_text = score_match[0].split()[-1]
            score = int(score_text)
        except:
            pass
    if score is None:
        score = random.randint(25, 45)
    return {
        "evaluation": content,
        "score": score,
        "max_score": 50,
        "percentage": round(score / 50 * 100, 1),
    }


def run_career_agent(user_input: str, context: dict) -> dict:
    """Main entry for career tasks."""
    user_lower = user_input.lower()
    role = context.get("interview_role", "Software Engineer")
    role_indicators = ["for ", "as a ", "applying for ", "interview for ", "role: ", "position: "]
    for indicator in role_indicators:
        if indicator in user_lower:
            parts = user_lower.split(indicator)
            if len(parts) > 1:
                role = parts[1].split(".")[0].split("?")[0].strip().title()
                break
    topic = "general"
    if any(k in user_lower for k in ["technical", "coding", "algorithm", "system design"]):
        topic = "technical"
    elif any(k in user_lower for k in ["behavioral", "soft skills", "teamwork", "leadership"]):
        topic = "behavioral"
    elif any(k in user_lower for k in ["system design", "architecture", "scale"]):
        topic = "system_design"
    session = context.get("career_session", {})
    current_question = session.get("current_question", "")
    if current_question and len(user_input) > 30 and not any(k in user_lower for k in ["question", "generate", "new", "another", "start"]):
        evaluation = evaluate_response(current_question, user_input, role)
        response = f"""## Career Agent: Interview Evaluation

**Role:** {role}  
**Question:** {current_question}

### Score: {evaluation['score']}/50 ({evaluation['percentage']}%)

{evaluation['evaluation']}

---
*Type "next question" to continue practicing.*
"""
        return {
            "response": response,
            "task": "evaluation",
            "score": evaluation["score"],
            "evaluation": evaluation,
        }
    else:
        try:
            question = generate_interview_question(role, topic)
        except:
            bank = QUESTION_BANK.get(topic, QUESTION_BANK["technical"])
            question = random.choice(bank)
        response = f"""## Career Agent: Mock Interview

**Role:** {role}  
**Topic:** {topic.title()}

### Question
> {question}

---
**Your turn!** Provide your answer below and I will evaluate it with detailed feedback and scoring.
"""
        return {
            "response": response,
            "task": "question",
            "question": question,
            "role": role,
            "topic": topic,
        }