import os
from dotenv import load_dotenv
from crewai import LLM

load_dotenv()


def get_llm(temperature: float = 0.4) -> LLM:
    return LLM(
        model=os.getenv("LEO_MODEL", "openai/gpt-oss-20b"),
        base_url=os.getenv("LEO_BASE_URL", "https://api.groq.com/openai/v1"),
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=temperature,
    )