from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from config import LabConfig, load_config
from memory_store import CompactMemoryManager, UserProfileStore, estimate_tokens, extract_profile_updates, generate_offline_answer
from model_provider import build_chat_model


@dataclass
class AgentContext:
    user_id: str
    memory_path: str


class AdvancedAgent:
    """Student TODO: implement Agent B / Advanced Agent.

    Required memory layers:
    1. within-session memory
    2. persistent `User.md`
    3. compact memory for long threads
    """

    def __init__(self, config: LabConfig | None = None, force_offline: bool = False) -> None:
        self.config = config or load_config()
        self.force_offline = force_offline
        self.profile_store = UserProfileStore(self.config.state_dir / "profiles")
        self.compact_memory = CompactMemoryManager(
            threshold_tokens=self.config.compact_threshold_tokens,
            keep_messages=self.config.compact_keep_messages,
        )
        self.thread_tokens: dict[str, int] = {}
        self.thread_prompt_tokens: dict[str, int] = {}
        self.current_user_id: str | None = None

        # Optionally initialize a real LangChain/LangGraph agent.
        self.langchain_agent = None

    def reply(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        """Student TODO: route between offline mode and live mode."""
        if self.force_offline or not self.config.model.api_key:
            return self._reply_offline(user_id, thread_id, message)

        self.current_user_id = user_id
        if self.langchain_agent is None:
            self._maybe_build_langchain_agent()

        # Offline sync to ensure facts are updated in User.md even in live mode
        new_facts = extract_profile_updates(message)
        existing_facts = self.profile_store.read_facts(user_id)
        existing_facts.update(new_facts)
        self.profile_store.write_facts(user_id, existing_facts)

        # Append to compact memory buffer
        self.compact_memory.append(thread_id, "user", message)

        # Calculate prompt token usage
        prompt_tokens = self._estimate_prompt_context_tokens(user_id, thread_id)
        self.thread_prompt_tokens[thread_id] = self.thread_prompt_tokens.get(thread_id, 0) + prompt_tokens

        # Invoke the live agent
        config_params = {"configurable": {"thread_id": thread_id}}
        res = self.langchain_agent.invoke(
            {"messages": [("user", message)]},
            config_params
        )

        last_msg = res["messages"][-1]
        response_text = last_msg.content

        # Append assistant reply to compact memory
        self.compact_memory.append(thread_id, "assistant", response_text)

        # Calculate output tokens
        response_tokens = estimate_tokens(response_text)
        self.thread_tokens[thread_id] = self.thread_tokens.get(thread_id, 0) + response_tokens

        return {
            "response": response_text,
            "prompt_tokens": prompt_tokens,
            "output_tokens": response_tokens
        }

    def token_usage(self, thread_id: str) -> int:
        return self.thread_tokens.get(thread_id, 0)

    def prompt_token_usage(self, thread_id: str) -> int:
        return self.thread_prompt_tokens.get(thread_id, 0)

    def memory_file_size(self, user_id: str) -> int:
        return self.profile_store.file_size(user_id)

    def compaction_count(self, thread_id: str) -> int:
        return self.compact_memory.compaction_count(thread_id)

    def _reply_offline(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        """Student TODO: implement the deterministic advanced path.

        Pseudocode:
        1. Extract stable profile facts from the incoming message.
        2. Persist those facts into `User.md`.
        3. Append the message into compact memory.
        4. Estimate prompt-context load from `User.md` + summary + recent messages.
        5. Generate a response that can answer long-term recall questions.
        6. Append the assistant reply and update token counters.
        """
        # 1. Extract facts
        new_facts = extract_profile_updates(message)

        # 2. Persist to User.md
        existing_facts = self.profile_store.read_facts(user_id)
        existing_facts.update(new_facts)
        self.profile_store.write_facts(user_id, existing_facts)

        # 3. Append to compact memory
        self.compact_memory.append(thread_id, "user", message)

        # 4. Estimate prompt context tokens
        prompt_tokens = self._estimate_prompt_context_tokens(user_id, thread_id)
        self.thread_prompt_tokens[thread_id] = self.thread_prompt_tokens.get(thread_id, 0) + prompt_tokens

        # 5. Generate reply
        response = self._offline_response(user_id, thread_id, message)

        # 6. Append reply to compact memory
        self.compact_memory.append(thread_id, "assistant", response)

        # 7. Update output tokens
        response_tokens = estimate_tokens(response)
        self.thread_tokens[thread_id] = self.thread_tokens.get(thread_id, 0) + response_tokens

        return {
            "response": response,
            "prompt_tokens": prompt_tokens,
            "output_tokens": response_tokens
        }

    def _estimate_prompt_context_tokens(self, user_id: str, thread_id: str) -> int:
        """Student TODO: estimate the context carried into one turn.

        Hint:
        - Include `User.md`
        - Include compact summary text
        - Include recent kept messages
        """
        # User.md tokens:
        user_md_content = self.profile_store.read_text(user_id)
        user_md_tokens = estimate_tokens(user_md_content)

        # Compact memory details:
        ctx = self.compact_memory.context(thread_id)
        summary_tokens = estimate_tokens(ctx.get("summary", ""))

        # Recent kept messages:
        messages = ctx.get("messages", [])
        messages_tokens = sum(estimate_tokens(msg["content"]) for msg in messages)

        return user_md_tokens + summary_tokens + messages_tokens

    def _offline_response(self, user_id: str, thread_id: str, message: str) -> str:
        """Student TODO: return a deterministic answer using persisted memory.

        Make sure the advanced agent can answer questions like:
        - "Mình tên gì?"
        - "Hiện tại mình làm nghề gì?"
        - "Nhắc lại style trả lời mình thích"
        - questions in the long stress dataset
        """
        facts = self.profile_store.read_facts(user_id)
        return generate_offline_answer(message, facts)

    def _maybe_build_langchain_agent(self):
        """Student TODO: wire a live agent with tools and compact middleware.

        High-level design:
        - `build_chat_model(self.config.model)` for the selected provider
        - `InMemorySaver` for short-term thread state
        - tool to read `User.md`
        - tool to write/edit `User.md`
        - dynamic prompt that injects profile memory
        - summarization middleware for long threads
        """
        if self.force_offline:
            return

        chat_model = build_chat_model(self.config.model)

        from langchain_core.tools import tool

        @tool
        def read_user_profile() -> str:
            """Read the user profile/persistent memory."""
            return self.profile_store.read_text(self.current_user_id or "")

        @tool
        def update_user_profile(content: str) -> str:
            """Write or overwrite the user profile with new content."""
            self.profile_store.write_text(self.current_user_id or "", content)
            return "Profile updated successfully."

        @tool
        def edit_user_profile(search_text: str, replacement: str) -> str:
            """Replace a specific text in the user profile."""
            success = self.profile_store.edit_text(self.current_user_id or "", search_text, replacement)
            return "Profile edited successfully." if success else "Search text not found in profile."

        tools = [read_user_profile, update_user_profile, edit_user_profile]

        from langgraph.checkpoint.memory import MemorySaver
        from langgraph.prebuilt import create_react_agent

        system_prompt = (
            "You are an advanced agent with persistent memory.\n"
            "You can read, update, or edit the user profile using tools.\n"
            "Always consult the user profile at the beginning of a session or when relevant.\n"
            "Keep the user profile clean, organized, and focused on stable facts."
        )

        self.langchain_agent = create_react_agent(
            chat_model,
            tools=tools,
            prompt=system_prompt,
            checkpointer=MemorySaver()
        )
