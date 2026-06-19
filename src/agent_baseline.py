from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from config import LabConfig, load_config
from memory_store import estimate_tokens
from model_provider import build_chat_model


@dataclass
class SessionState:
    messages: list[dict[str, str]] = field(default_factory=list)
    token_usage: int = 0
    prompt_tokens_processed: int = 0


class BaselineAgent:
    """Student TODO: implement Agent A.

    Requirements:
    - Within-session memory only
    - No persistent `User.md`
    - Should forget long-term facts across new threads
    """

    def __init__(self, config: LabConfig | None = None, force_offline: bool = False) -> None:
        self.config = config or load_config()
        self.force_offline = force_offline
        self.sessions: dict[str, SessionState] = {}

        # Optionally initialize a real LangChain/LangGraph agent when dependencies exist.
        self.langchain_agent = None

    def reply(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        """Student TODO: return the agent response and token accounting.

        Pseudocode:
        - If a live agent exists, call the live path.
        - Otherwise use a deterministic offline path.
        """
        if self.force_offline or not self.config.model.api_key:
            return self._reply_offline(thread_id, message)

        if self.langchain_agent is None:
            self._maybe_build_langchain_agent()

        state = self.sessions.setdefault(thread_id, SessionState())
        state.messages.append({"role": "user", "content": message})

        # Process prompt tokens up to user message
        turn_prompt_tokens = sum(estimate_tokens(msg["content"]) for msg in state.messages)
        state.prompt_tokens_processed += turn_prompt_tokens

        config_params = {"configurable": {"thread_id": thread_id}}
        res = self.langchain_agent.invoke(
            {"messages": [("user", message)]},
            config_params
        )

        last_msg = res["messages"][-1]
        response_text = last_msg.content

        state.messages.append({"role": "assistant", "content": response_text})

        turn_output_tokens = estimate_tokens(response_text)
        state.token_usage += turn_output_tokens

        return {
            "response": response_text,
            "prompt_tokens": turn_prompt_tokens,
            "output_tokens": turn_output_tokens
        }

    def token_usage(self, thread_id: str) -> int:
        if thread_id in self.sessions:
            return self.sessions[thread_id].token_usage
        return 0

    def prompt_token_usage(self, thread_id: str) -> int:
        if thread_id in self.sessions:
            return self.sessions[thread_id].prompt_tokens_processed
        return 0

    def compaction_count(self, thread_id: str) -> int:
        # Baseline has no compact memory.
        return 0

    def _reply_offline(self, thread_id: str, message: str) -> dict[str, Any]:
        """Student TODO: implement a simple offline behavior.

        Suggested behavior:
        - Store the new user message in the session
        - Generate a short deterministic reply
        - Update token counts
        - Never remember facts across different thread ids
        """
        state = self.sessions.setdefault(thread_id, SessionState())

        # 1. Append user message
        state.messages.append({"role": "user", "content": message})

        # 2. Calculate prompt tokens for this turn
        turn_prompt_tokens = sum(estimate_tokens(msg["content"]) for msg in state.messages)
        state.prompt_tokens_processed += turn_prompt_tokens

        # 3. Extract facts from current session messages to answer
        from memory_store import extract_profile_updates, generate_offline_answer
        session_facts = {}
        for msg in state.messages:
            if msg["role"] == "user":
                session_facts.update(extract_profile_updates(msg["content"]))

        # 4. Generate deterministic reply
        response = generate_offline_answer(message, session_facts)

        # 5. Append assistant reply
        state.messages.append({"role": "assistant", "content": response})

        # 6. Update output token count
        turn_output_tokens = estimate_tokens(response)
        state.token_usage += turn_output_tokens

        return {
            "response": response,
            "prompt_tokens": turn_prompt_tokens,
            "output_tokens": turn_output_tokens
        }

    def _maybe_build_langchain_agent(self):
        """Student TODO: optionally wire `create_agent` + `InMemorySaver` here.

        Use `build_chat_model(self.config.model)` so the baseline can run with any supported provider.
        """
        if self.force_offline:
            return

        chat_model = build_chat_model(self.config.model)
        from langgraph.checkpoint.memory import MemorySaver
        from langgraph.prebuilt import create_react_agent

        self.langchain_agent = create_react_agent(
            chat_model,
            tools=[],
            checkpointer=MemorySaver()
        )
