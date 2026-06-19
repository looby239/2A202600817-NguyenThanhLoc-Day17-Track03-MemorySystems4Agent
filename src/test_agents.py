from __future__ import annotations

from pathlib import Path

from agent_advanced import AdvancedAgent
from agent_baseline import BaselineAgent
from config import load_config


def make_config(tmp_path: Path):
    """Student TODO: build an isolated config for tests."""
    from config import LabConfig
    from model_provider import ProviderConfig
    
    # Point state_dir and other directories to isolated tmp_path
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    
    return LabConfig(
        base_dir=tmp_path,
        data_dir=tmp_path / "data",
        state_dir=state_dir,
        compact_threshold_tokens=50,
        compact_keep_messages=2,
        model=ProviderConfig(provider="openai", model_name="gpt-4o", temperature=0.0),
        judge_model=ProviderConfig(provider="openai", model_name="gpt-4o", temperature=0.0),
    )


def test_user_markdown_read_write_edit(tmp_path: Path) -> None:
    """Student TODO: verify `User.md` can be created, updated, and edited."""
    from memory_store import UserProfileStore
    
    config = make_config(tmp_path)
    store = UserProfileStore(config.state_dir / "profiles")
    user_id = "test_user_crud"
    
    # Verify write
    store.write_text(user_id, "Line 1: data 1\nLine 2: data 2")
    assert store.read_text(user_id) == "Line 1: data 1\nLine 2: data 2"
    
    # Verify edit
    changed = store.edit_text(user_id, "data 1", "new data 1")
    assert changed is True
    assert store.read_text(user_id) == "Line 1: new data 1\nLine 2: data 2"
    
    # Verify size
    assert store.file_size(user_id) > 0


def test_compact_trigger(tmp_path: Path) -> None:
    """Student TODO: verify long threads trigger compaction."""
    from memory_store import CompactMemoryManager
    
    # Set compaction threshold to 15, keep recent 2 messages
    mgr = CompactMemoryManager(threshold_tokens=15, keep_messages=2)
    
    # Each of these messages has ~25 characters, which is ~6 tokens.
    mgr.append("thread-1", "user", "This is the first message.")
    mgr.append("thread-1", "assistant", "This is the second message.")
    
    # Total buffer size = 2 messages, total tokens ~ 12. No compaction.
    assert mgr.compaction_count("thread-1") == 0
    
    # Append third message. Total tokens ~ 18 > 15, and len = 3 > 2. Compaction should trigger.
    mgr.append("thread-1", "user", "This is the third message.")
    assert mgr.compaction_count("thread-1") == 1
    
    ctx = mgr.context("thread-1")
    assert len(ctx["messages"]) == 2
    assert ctx["summary"] != ""


def test_cross_session_recall(tmp_path: Path) -> None:
    """Student TODO: verify advanced remembers across sessions and baseline does not."""
    config = make_config(tmp_path)
    
    # Initialize both in offline mode
    baseline = BaselineAgent(config, force_offline=True)
    advanced = AdvancedAgent(config, force_offline=True)
    
    # Provide name info in thread 1
    baseline.reply("user-1", "thread-1", "Chào bạn, mình tên là DũngCT.")
    advanced.reply("user-1", "thread-1", "Chào bạn, mình tên là DũngCT.")
    
    # Ask in thread 2
    res_b = baseline.reply("user-1", "thread-2", "Mình tên gì?")
    res_a = advanced.reply("user-1", "thread-2", "Mình tên gì?")
    
    # Baseline has no cross-session memory, should not recall
    assert "DũngCT" not in res_b["response"]
    
    # Advanced has User.md, should recall
    assert "DũngCT" in res_a["response"]


def test_compact_reduces_prompt_load_on_long_thread(tmp_path: Path) -> None:
    """Student TODO: compare prompt load of baseline vs advanced on a long thread."""
    config = make_config(tmp_path)
    config.compact_threshold_tokens = 30
    config.compact_keep_messages = 2
    
    baseline = BaselineAgent(config, force_offline=True)
    advanced = AdvancedAgent(config, force_offline=True)
    
    # Feed 10 turns of messaging to both agents
    for i in range(10):
        msg = f"This is user message number {i} in the conversation."
        baseline.reply("user-1", "thread-long", msg)
        advanced.reply("user-1", "thread-long", msg)
        
    # Baseline keeps all previous turns, so prompt tokens grow quadratically
    # Advanced compacts old turns, so prompt tokens are capped / grow much slower
    assert advanced.prompt_token_usage("thread-long") < baseline.prompt_token_usage("thread-long")
