from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProviderConfig:
    """Student TODO: define the provider configuration shared by the agents.

    Required providers for this lab:
    - openai
    - custom (OpenAI-compatible base URL)
    - gemini
    - anthropic
    - ollama
    - openrouter
    """

    provider: str
    model_name: str
    temperature: float
    api_key: str | None = None
    base_url: str | None = None


def normalize_provider(value: str) -> str:
    """Student TODO: map aliases like `anthorpic` -> `anthropic`."""
    val = value.strip().lower()
    if val in ["openai", "open-ai"]:
        return "openai"
    elif val in ["gemini", "google", "google-genai"]:
        return "gemini"
    elif val in ["anthropic", "anthorpic"]:
        return "anthropic"
    elif val in ["ollama"]:
        return "ollama"
    elif val in ["openrouter"]:
        return "openrouter"
    elif val in ["custom"]:
        return "custom"
    return val


def build_chat_model(config: ProviderConfig):
    """Student TODO: instantiate the real chat model for the selected provider.

    Pseudocode:
    - `openai` -> `ChatOpenAI`
    - `custom` -> `ChatOpenAI` with `base_url`
    - `gemini` -> `ChatGoogleGenerativeAI`
    - `anthropic` -> `ChatAnthropic`
    - `ollama` -> `ChatOllama`
    - `openrouter` -> `ChatOpenRouter`
    """
    prov = normalize_provider(config.provider)
    model_name = config.model_name
    temp = config.temperature

    if prov == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model_name, temperature=temp, openai_api_key=config.api_key)
    elif prov == "custom":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model_name, temperature=temp, base_url=config.base_url, openai_api_key=config.api_key)
    elif prov == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=model_name, temperature=temp, google_api_key=config.api_key)
    elif prov == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model_name, temperature=temp, api_key=config.api_key)
    elif prov == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(model=model_name, temperature=temp, base_url=config.base_url)
    elif prov == "openrouter":
        from langchain_openrouter import ChatOpenRouter
        return ChatOpenRouter(model=model_name, temperature=temp, api_key=config.api_key)
    else:
        raise ValueError(f"Unsupported provider: {config.provider}")

