import os
from dotenv import load_dotenv
from pathlib import Path
from langchain_openai import ChatOpenAI

# Search for .env in current + parent directories
env_path = None
for p in [Path.cwd()] + list(Path.cwd().parents[:5]):
    candidate = p / ".env"
    if candidate.exists():
        env_path = candidate
        break
if env_path:
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()


def get_kimi_client(temperature=0.3, max_tokens=4096, **kwargs):
    """Returns a ChatOpenAI client pointing to Groq (or Kimi if you change base URL)."""
    api_key = os.getenv("GROQ_API_KEY") or os.getenv("KIMI_API_KEY")
    if not api_key:
        raise ValueError("No API key found. Set GROQ_API_KEY or KIMI_API_KEY in your .env file.")

    base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

    return ChatOpenAI(
        openai_api_key=api_key,
        openai_api_base=base_url,
        model_name=model,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs
    )

# Alias for backward compatibility
get_llm = get_kimi_client