from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_advanced import AdvancedAgent
from agent_baseline import BaselineAgent
from config import load_config


@dataclass
class BenchmarkRow:
    agent_name: str
    agent_tokens_only: int
    prompt_tokens_processed: int
    recall_score: float
    response_quality: float
    memory_growth_bytes: int
    compactions: int


def load_conversations(path: Path) -> list[dict[str, Any]]:
    """Student TODO: read JSON conversations from disk."""
    import json
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def recall_points(answer: str, expected: list[str]) -> float:
    """Student TODO: return 0 / 0.5 / 1 depending on how many expected facts appear."""
    if not expected:
        return 1.0
    answer_lower = answer.lower()
    matched = sum(1 for item in expected if item.lower() in answer_lower)
    if matched == 0:
        return 0.0
    elif matched == len(expected):
        return 1.0
    else:
        return 0.5


def heuristic_quality(answer: str, expected: list[str]) -> float:
    """Student TODO: add a lightweight quality score for offline mode."""
    r_score = recall_points(answer, expected)
    if r_score == 0.0:
        return 0.0
    if "tôi không biết" in answer.lower():
        return 0.0

    expected_len = len(expected)
    if expected_len > 0:
        ratio = len(answer) / expected_len
        # Heuristic: penalize response if it's too long compared to expected fact count
        if ratio > 150:
            conciseness_factor = 0.7
        else:
            conciseness_factor = 1.0
    else:
        conciseness_factor = 1.0

    return r_score * conciseness_factor


def run_agent_benchmark(agent_name: str, agent, conversations: list[dict[str, Any]], config) -> BenchmarkRow:
    """Student TODO: evaluate one agent over many conversations.

    Pseudocode:
    1. Feed all turns to the agent.
    2. Track `agent tokens only`.
    3. Track `prompt tokens processed`.
    4. Ask recall questions in a fresh thread.
    5. Compute average recall and quality.
    6. Record memory file growth and compaction count.
    """
    import shutil

    # Collect unique users to measure their memory sizes
    user_ids = {conv["user_id"] for conv in conversations}
    initial_sizes = {}
    for uid in user_ids:
        if hasattr(agent, "memory_file_size"):
            initial_sizes[uid] = agent.memory_file_size(uid)
        else:
            initial_sizes[uid] = 0

    recall_scores = []
    quality_scores = []
    active_threads = []

    for conv in conversations:
        user_id = conv["user_id"]
        thread_id = conv["id"]
        active_threads.append(thread_id)

        # 1. Feed all turns to the agent
        for turn in conv["turns"]:
            agent.reply(user_id, thread_id, turn)
            if not agent.force_offline:
                import time
                time.sleep(3.0)

        # 2. Ask recall questions in a fresh thread
        for q_idx, q_item in enumerate(conv["recall_questions"]):
            q_text = q_item["question"]
            expected = q_item["expected_contains"]

            q_thread_id = f"{thread_id}-recall-{q_idx}"
            active_threads.append(q_thread_id)

            res = agent.reply(user_id, q_thread_id, q_text)
            answer = res.get("response", "") if isinstance(res, dict) else str(res)

            if not agent.force_offline:
                import time
                time.sleep(3.0)

            r_score = recall_points(answer, expected)
            q_score = heuristic_quality(answer, expected)

            recall_scores.append(r_score)
            quality_scores.append(q_score)

    # 3. Sum up token metrics
    total_agent_tokens = sum(agent.token_usage(tid) for tid in active_threads)
    total_prompt_tokens = sum(agent.prompt_token_usage(tid) for tid in active_threads)
    total_compactions = sum(agent.compaction_count(tid) for tid in active_threads)

    # 4. Measure final memory growth
    final_sizes = {}
    for uid in user_ids:
        if hasattr(agent, "memory_file_size"):
            final_sizes[uid] = agent.memory_file_size(uid)
        else:
            final_sizes[uid] = 0

    memory_growth = sum(final_sizes[uid] - initial_sizes[uid] for uid in user_ids)
    avg_recall = sum(recall_scores) / len(recall_scores) if recall_scores else 0.0
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

    return BenchmarkRow(
        agent_name=agent_name,
        agent_tokens_only=total_agent_tokens,
        prompt_tokens_processed=total_prompt_tokens,
        recall_score=avg_recall,
        response_quality=avg_quality,
        memory_growth_bytes=memory_growth,
        compactions=total_compactions,
    )


def format_rows(rows: list[BenchmarkRow]) -> str:
    """Student TODO: print a markdown table or tabulated output."""
    from tabulate import tabulate
    headers = [
        "Agent Name",
        "Agent tokens only",
        "Prompt tokens processed",
        "Cross-session recall",
        "Response quality",
        "Memory growth (bytes)",
        "Compactions",
    ]
    data = []
    for r in rows:
        data.append([
            r.agent_name,
            r.agent_tokens_only,
            r.prompt_tokens_processed,
            f"{r.recall_score:.2%}",
            f"{r.response_quality:.2%}",
            r.memory_growth_bytes,
            r.compactions,
        ])
    return tabulate(data, headers=headers, tablefmt="github")


def main() -> None:
    """Student TODO: run both benchmark suites.

    Required benchmark sections:
    - Standard benchmark from `data/conversations.json`
    - Long-context stress benchmark from `data/advanced_long_context.json`

    Compare:
    - Baseline
    - Advanced

    Keep the same output columns as the solved lab:
    - Agent tokens only
    - Prompt tokens processed
    - Cross-session recall
    - Response quality
    - Memory growth (bytes)
    - Compactions
    """
    import shutil

    config = load_config(Path(__file__).resolve().parent.parent)

    standard_dataset = load_conversations(config.data_dir / "conversations.json")
    stress_dataset = load_conversations(config.data_dir / "advanced_long_context.json")

    print("=== STANDARD BENCHMARK ===")
    # Clear state dir to make clean benchmark for Baseline
    if config.state_dir.exists():
        shutil.rmtree(config.state_dir)
    config.state_dir.mkdir(parents=True, exist_ok=True)
    baseline_std = BaselineAgent(config, force_offline=False)
    row_b_std = run_agent_benchmark("Baseline Agent", baseline_std, standard_dataset, config)

    # Reset state dir for Advanced Agent clean run
    if config.state_dir.exists():
        shutil.rmtree(config.state_dir)
    config.state_dir.mkdir(parents=True, exist_ok=True)
    advanced_std = AdvancedAgent(config, force_offline=False)
    row_a_std = run_agent_benchmark("Advanced Agent", advanced_std, standard_dataset, config)

    print(format_rows([row_b_std, row_a_std]))
    print("\n")

    print("=== LONG-CONTEXT STRESS BENCHMARK ===")
    # Reset state dir for Baseline
    if config.state_dir.exists():
        shutil.rmtree(config.state_dir)
    config.state_dir.mkdir(parents=True, exist_ok=True)
    baseline_stress = BaselineAgent(config, force_offline=False)
    row_b_stress = run_agent_benchmark("Baseline Agent", baseline_stress, stress_dataset, config)

    # Reset state dir for Advanced
    if config.state_dir.exists():
        shutil.rmtree(config.state_dir)
    config.state_dir.mkdir(parents=True, exist_ok=True)
    advanced_stress = AdvancedAgent(config, force_offline=False)
    row_a_stress = run_agent_benchmark("Advanced Agent", advanced_stress, stress_dataset, config)

    print(format_rows([row_b_stress, row_a_stress]))


if __name__ == "__main__":
    main()
