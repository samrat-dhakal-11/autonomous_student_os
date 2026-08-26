"""LangGraph Master Router Agent — orchestrates all sub-agents."""
import json
from typing import TypedDict, Annotated, Sequence, Literal
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from utils.llm_config import get_kimi_client


class AgentState(TypedDict):
    """Shared state across the LangGraph."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    active_agent: str
    agent_output: dict
    context: dict


INTENT_PROMPT = """You are the Master Router of the Autonomous Student OS.
Analyze the user's message and classify intent into ONE category:

- "productivity" -> file organization, sorting, cleaning downloads, managing files
- "academics" -> code debugging, programming help, PDF reading, research papers, study help
- "finance" -> expenses, budget, bank statements, spending analysis, savings
- "career" -> interview prep, resume, job applications, mock interviews, behavioral questions
- "chat" -> general conversation, greeting, unclear intent

Respond ONLY with a JSON object: {"intent": "<category>", "confidence": 0.0-1.0, "reason": "..."}
"""


def classify_intent(state: AgentState) -> dict:
    """Classify user intent using Kimi."""
    client = get_kimi_client(temperature=0.1, max_tokens=256)
    last_msg = state["messages"][-1].content if state["messages"] else ""
    prompt = f"{INTENT_PROMPT}\n\nUser message: \"{last_msg}\""
    response = client.invoke([HumanMessage(content=prompt)])
    try:
        result = json.loads(response.content)
        intent = result.get("intent", "chat")
        confidence = result.get("confidence", 0.5)
    except (json.JSONDecodeError, Exception):
        intent = "chat"
        confidence = 0.5
        result = {"intent": "chat", "confidence": 0.5, "reason": "fallback"}
    return {
        "messages": state["messages"],
        "active_agent": intent if confidence > 0.4 else "chat",
        "agent_output": result,
        "context": state.get("context", {}),
    }


def productivity_node(state: AgentState) -> dict:
    """Delegate to Productivity Agent."""
    from agents.productivity import run_productivity_agent
    output = run_productivity_agent(state["messages"][-1].content, state.get("context", {}))
    return {
        "messages": state["messages"] + [AIMessage(content=output.get("response", ""))],
        "active_agent": "productivity",
        "agent_output": output,
        "context": {**state.get("context", {}), "productivity": output},
    }


def academics_node(state: AgentState) -> dict:
    """Delegate to Academics Agent."""
    from agents.academics import run_academics_agent
    output = run_academics_agent(state["messages"][-1].content, state.get("context", {}))
    return {
        "messages": state["messages"] + [AIMessage(content=output.get("response", ""))],
        "active_agent": "academics",
        "agent_output": output,
        "context": {**state.get("context", {}), "academics": output},
    }


def finance_node(state: AgentState) -> dict:
    """Delegate to Finance Agent."""
    from agents.finance import run_finance_agent
    output = run_finance_agent(state["messages"][-1].content, state.get("context", {}))
    return {
        "messages": state["messages"] + [AIMessage(content=output.get("response", ""))],
        "active_agent": "finance",
        "agent_output": output,
        "context": {**state.get("context", {}), "finance": output},
    }


def career_node(state: AgentState) -> dict:
    """Delegate to Career Agent."""
    from agents.career import run_career_agent
    output = run_career_agent(state["messages"][-1].content, state.get("context", {}))
    return {
        "messages": state["messages"] + [AIMessage(content=output.get("response", ""))],
        "active_agent": "career",
        "agent_output": output,
        "context": {**state.get("context", {}), "career": output},
    }


def chat_node(state: AgentState) -> dict:
    """General chat fallback."""
    client = get_kimi_client(temperature=0.7, max_tokens=1024)
    response = client.invoke(state["messages"])
    return {
        "messages": state["messages"] + [response],
        "active_agent": "chat",
        "agent_output": {"response": response.content},
        "context": state.get("context", {}),
    }


def route_decision(state: AgentState) -> Literal["productivity", "academics", "finance", "career", "chat"]:
    """Route to the appropriate agent based on classified intent."""
    return state.get("active_agent", "chat")


def build_router_graph() -> StateGraph:
    """Construct and compile the Master Router LangGraph."""
    workflow = StateGraph(AgentState)
    workflow.add_node("classify", classify_intent)
    workflow.add_node("productivity", productivity_node)
    workflow.add_node("academics", academics_node)
    workflow.add_node("finance", finance_node)
    workflow.add_node("career", career_node)
    workflow.add_node("chat", chat_node)
    workflow.set_entry_point("classify")
    workflow.add_conditional_edges(
        "classify",
        route_decision,
        {
            "productivity": "productivity",
            "academics": "academics",
            "finance": "finance",
            "career": "career",
            "chat": "chat",
        },
    )
    workflow.add_edge("productivity", END)
    workflow.add_edge("academics", END)
    workflow.add_edge("finance", END)
    workflow.add_edge("career", END)
    workflow.add_edge("chat", END)
    return workflow.compile()


_router_graph = None


def get_router_graph():
    """Get or create the compiled router graph."""
    global _router_graph
    if _router_graph is None:
        _router_graph = build_router_graph()
    return _router_graph


def run_master_router(user_input: str, context: dict = None) -> dict:
    """Main entry point: route a user message through the agent system."""
    graph = get_router_graph()
    state = {
        "messages": [HumanMessage(content=user_input)],
        "active_agent": "chat",
        "agent_output": {},
        "context": context or {},
    }
    try:
        result = graph.invoke(state)
        last_ai_msg = None
        for msg in reversed(result["messages"]):
            if isinstance(msg, AIMessage):
                last_ai_msg = msg
                break
        return {
            "response": last_ai_msg.content if last_ai_msg else "No response generated.",
            "agent": result["active_agent"],
            "output": result["agent_output"],
            "messages": result["messages"],
        }
    except Exception as e:
        return {
            "response": f"System Error: {str(e)}\n\nPlease check your KIMI_API_KEY configuration.",
            "agent": "error",
            "output": {},
            "messages": state["messages"],
        }