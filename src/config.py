from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from model_provider import ProviderConfig


@dataclass
class LabConfig:
    """Student TODO: define the shared configuration for the lab.

    Hints:
    - Keep paths for the repo root, dataset directory, and state directory.
    - Add compact-memory settings such as threshold and number of messages to keep.
    - Add provider settings for `openai`, `custom`, `gemini`, `anthropic`, `ollama`, and `openrouter`.
    """

    base_dir: Path
    data_dir: Path
    state_dir: Path
    compact_threshold_tokens: int
    compact_keep_messages: int
    model: ProviderConfig
    judge_model: ProviderConfig


import os
import dotenv


def load_config(base_dir: Path | None = None) -> LabConfig:
    """Student TODO: load environment variables and return a LabConfig.

    Pseudocode:
    1. Resolve the repo root or default to the current file parent.
    2. Optionally load values from `.env`.
    3. Create `state/` if it does not exist.
    4. Return a populated LabConfig instance.
    """

    root = (base_dir or Path(__file__).resolve().parent.parent).resolve()

    # Load .env if present
    dotenv.load_dotenv(root / ".env")

    provider = os.getenv("LLM_PROVIDER", "openai")
    model_name = os.getenv("LLM_MODEL", "gpt-4o")
    temperature_str = os.getenv("LLM_TEMPERATURE", "0.0")
    try:
        temperature = float(temperature_str)
    except ValueError:
        temperature = 0.0

    # Read API keys and base URLs
    openai_key = os.getenv("OPENAI_API_KEY", "")
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
    custom_key = os.getenv("CUSTOM_API_KEY", "")

    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    custom_url = os.getenv("CUSTOM_BASE_URL", "")

    # Map provider config API key and base URL
    prov = provider.strip().lower()
    api_key = None
    base_url = None
    if prov in ["openai", "open-ai"]:
        api_key = openai_key
    elif prov in ["gemini", "google", "google-genai"]:
        api_key = gemini_key
    elif prov in ["anthropic", "anthorpic"]:
        api_key = anthropic_key
    elif prov in ["openrouter"]:
        api_key = openrouter_key
    elif prov in ["ollama"]:
        base_url = ollama_url
    elif prov in ["custom"]:
        api_key = custom_key
        base_url = custom_url

    model_config = ProviderConfig(
        provider=provider,
        model_name=model_name,
        temperature=temperature,
        api_key=api_key,
        base_url=base_url
    )

    # Sensible defaults for judge model (same as primary model if not specified)
    judge_provider = os.getenv("JUDGE_PROVIDER", provider)
    judge_model_name = os.getenv("JUDGE_MODEL", model_name)
    judge_model_config = ProviderConfig(
        provider=judge_provider,
        model_name=judge_model_name,
        temperature=0.0,
        api_key=api_key,
        base_url=base_url
    )

    state_dir = root / "state"
    state_dir.mkdir(parents=True, exist_ok=True)

    compact_threshold_tokens = int(os.getenv("COMPACT_THRESHOLD_TOKENS", "1000"))
    compact_keep_messages = int(os.getenv("COMPACT_KEEP_MESSAGES", "6"))

    return LabConfig(
        base_dir=root,
        data_dir=root / "data",
        state_dir=state_dir,
        compact_threshold_tokens=compact_threshold_tokens,
        compact_keep_messages=compact_keep_messages,
        model=model_config,
        judge_model=judge_model_config,
    )

