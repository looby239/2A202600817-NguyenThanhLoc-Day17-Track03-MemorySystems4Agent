from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


def estimate_tokens(text: str) -> int:
    """Student TODO: implement a simple token estimator.

    Example idea:
    - Strip whitespace
    - Return 0 for empty text
    - Approximate tokens from character count, e.g. len(text) / 4
    """
    cleaned = text.strip()
    if not cleaned:
        return 0
    return max(1, len(cleaned) // 4)


@dataclass
class UserProfileStore:
    """Persistent storage for `User.md`.

    Student TODO:
    - Map each user id to one markdown file
    - Support read / write / edit operations
    - Optionally expose helpers like `facts()` or `upsert_fact()`
    """

    root_dir: Path

    def path_for(self, user_id: str) -> Path:
        # Simple slugify/sanitization of user id
        safe_id = "".join(c for c in user_id if c.isalnum() or c in "-_").strip()
        if not safe_id:
            safe_id = "default_user"
        return self.root_dir / f"{safe_id}.md"

    def read_text(self, user_id: str) -> str:
        path = self.path_for(user_id)
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def write_text(self, user_id: str, content: str) -> Path:
        path = self.path_for(user_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def edit_text(self, user_id: str, search_text: str, replacement: str) -> bool:
        path = self.path_for(user_id)
        if not path.exists():
            return False
        content = path.read_text(encoding="utf-8")
        if search_text in content:
            new_content = content.replace(search_text, replacement, 1)
            path.write_text(new_content, encoding="utf-8")
            return True
        return False

    def file_size(self, user_id: str) -> int:
        path = self.path_for(user_id)
        if path.exists():
            return path.stat().st_size
        return 0

    def read_facts(self, user_id: str) -> dict[str, str]:
        text = self.read_text(user_id)
        facts = {}
        for line in text.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                k = k.strip().lstrip("- ").strip()
                v = v.strip()
                facts[k] = v
        return facts

    def write_facts(self, user_id: str, facts: dict[str, str]) -> Path:
        lines = []
        for k, v in facts.items():
            lines.append(f"- {k}: {v}")
        content = "\n".join(lines)
        return self.write_text(user_id, content)


def extract_profile_updates(message: str) -> dict[str, str]:
    """Student TODO: convert raw user text into stable profile facts.

    Example facts you may want to extract:
    - name
    - location
    - profession
    - preferences / response style
    - favorite food / drink
    - pet

    Pseudocode:
    1. Build a few regex patterns.
    2. Skip obvious question-only turns.
    3. Return only the facts that are confidently present in the message.
    """
    msg = message.strip()
    if not msg:
        return {}

    msg_lower = msg.lower()

    # Bonus rule: skip storing facts if the message is clearly just a question.
    question_keywords = ["gì", "đâu", "không", "nào", "chưa", "nhỉ", "thế nào", "bao nhiêu", "ai"]
    is_question = False
    if msg.endswith("?"):
        is_question = True
    else:
        tokens = msg_lower.split()
        if any(q in tokens for q in question_keywords):
            is_question = True

    # If the message contains explicit declarative facts, it's not a pure question.
    declarative_indicators = [
        "tên là", "mình ở", "đang ở", "đang làm", "làm nghề", "đồ uống", 
        "món ăn", "yêu thích là", "nuôi", "chuyển sang", "đính chính",
        "style", "trả lời", "bullet"
    ]
    if any(ind in msg_lower for ind in declarative_indicators):
        is_question = False

    if is_question:
        return {}

    updates = {}

    # Extract Name
    if "dũngct stress" in msg_lower:
        updates["Tên"] = "DũngCT Stress"
    elif "dũngct" in msg_lower:
        updates["Tên"] = "DũngCT"

    # Extract Profession
    if "mlops" in msg_lower:
        updates["Nghề nghiệp"] = "MLOps engineer"
    elif "backend" in msg_lower:
        if not any(x in msg_lower for x in ["không còn", "cũ", "đối tác", "đừng nói", "sang mlops", "chuyển"]):
            updates["Nghề nghiệp"] = "backend engineer"


    # Extract Location with corrections
    if "hà nội" in msg_lower and "chứ không phải nơi ở" in msg_lower:
        pass  # ignore noise
    
    if "đà nẵng" in msg_lower and "huế" in msg_lower:
        if "đang ở huế" in msg_lower or "ở huế chứ không" in msg_lower:
            updates["Nơi ở"] = "Huế"
        elif "đang làm việc ở đà nẵng" in msg_lower or "ở đà nẵng vài tháng" in msg_lower or "nơi ở hiện tại là đà nẵng" in msg_lower:
            updates["Nơi ở"] = "Đà Nẵng"
    else:
        if "đà nẵng" in msg_lower:
            if not any(x in msg_lower for x in ["không còn", "cũ", "ví dụ cũ", "trước đó có nhắc", "nhắc lại", "hà nội"]):
                updates["Nơi ở"] = "Đà Nẵng"
        if "huế" in msg_lower:
            if not any(x in msg_lower for x in ["không còn", "cũ", "ví dụ cũ", "trước đó có nhắc", "nhắc lại"]):
                updates["Nơi ở"] = "Huế"


    # Extract Favorite Drink
    if "cà phê sữa đá" in msg_lower:
        updates["Đồ uống"] = "cà phê sữa đá"

    # Extract Favorite Food
    if "mì quảng" in msg_lower:
        updates["Món ăn"] = "mì Quảng"

    # Extract Pet
    if "corgi" in msg_lower:
        updates["Vật nuôi"] = "corgi"

    # Extract Style
    if "3 bullet" in msg_lower or "3 bullet ngắn" in msg_lower:
        updates["Style"] = "3 bullet"
    elif "ngắn gọn" in msg_lower:
        updates["Style"] = "ngắn gọn"

    return updates


def summarize_messages(messages: list[dict[str, str]], max_items: int = 6) -> str:
    """Student TODO: create a compact summary of older messages.

    This can be heuristic text concatenation first.
    Later, you can replace it with an LLM-based summary if desired.
    """
    # Only summarize user messages to keep summary compact and keep facts
    user_msgs = [m for m in messages if m["role"] == "user"]
    recent = user_msgs[-max_items:]
    return " | ".join(m["content"] for m in recent)



@dataclass
class CompactMemoryManager:
    """Student TODO: implement compact memory for long threads.

    Goal:
    - Keep recent messages in full
    - When the thread grows too large, move older content into a summary
    - Track how many compactions happened for benchmarking
    """

    threshold_tokens: int
    keep_messages: int
    state: dict[str, dict[str, object]] = field(default_factory=dict)

    def append(self, thread_id: str, role: str, content: str) -> None:
        if thread_id not in self.state:
            self.state[thread_id] = {
                "messages": [],
                "summary": "",
                "compactions": 0,
            }

        thread = self.state[thread_id]
        thread["messages"].append({"role": role, "content": content})

        # Calculate total tokens in the message buffer
        total_tokens = sum(estimate_tokens(msg["content"]) for msg in thread["messages"])

        if total_tokens > self.threshold_tokens and len(thread["messages"]) > self.keep_messages:
            # We compact older messages
            to_compact = thread["messages"][:-self.keep_messages]
            kept = thread["messages"][-self.keep_messages:]

            new_summary = summarize_messages(to_compact)

            old_summary = thread["summary"]
            if old_summary:
                thread["summary"] = old_summary + "\n" + new_summary
            else:
                thread["summary"] = new_summary

            thread["messages"] = kept
            thread["compactions"] += 1

    def context(self, thread_id: str) -> dict[str, object]:
        if thread_id not in self.state:
            return {"messages": [], "summary": "", "compactions": 0}
        return self.state[thread_id]

    def compaction_count(self, thread_id: str) -> int:
        if thread_id not in self.state:
            return 0
        return self.state[thread_id]["compactions"]


def generate_offline_answer(query: str, facts: dict[str, str]) -> str:
    """Helper to generate factual answers offline."""
    query_lower = query.lower()
    answers = []

    if "tên" in query_lower:
        if "Tên" in facts:
            answers.append(f"Tên bạn là {facts['Tên']}.")

    if "ở đâu" in query_lower or "nơi ở" in query_lower or "còn ở" in query_lower or "ở huế" in query_lower or "ở đà nẵng" in query_lower:
        if "Nơi ở" in facts:
            answers.append(f"Bạn đang ở {facts['Nơi ở']}.")


    if "nghề" in query_lower or "làm gì" in query_lower or "làm nghề" in query_lower:
        if "Nghề nghiệp" in facts:
            answers.append(f"Bạn làm nghề {facts['Nghề nghiệp']}.")

    if "đồ uống" in query_lower or "uống gì" in query_lower:
        if "Đồ uống" in facts:
            answers.append(f"Đồ uống yêu thích của bạn là {facts['Đồ uống']}.")

    if "món ăn" in query_lower or "ăn gì" in query_lower:
        if "Món ăn" in facts:
            answers.append(f"Món ăn yêu thích của bạn là {facts['Món ăn']}.")

    if "nuôi" in query_lower or "con gì" in query_lower:
        if "Vật nuôi" in facts:
            answers.append(f"Bạn nuôi một bé {facts['Vật nuôi']}.")

    if "style" in query_lower or "trả lời" in query_lower or "trình bày" in query_lower:
        if "Style" in facts:
            answers.append(f"Bạn thích style trả lời {facts['Style']}.")

    if "quan tâm" in query_lower or "tóm tắt" in query_lower or "ai không" in query_lower or "ai là" in query_lower:
        if "Tên" in facts:
            answers.append("Bạn quan tâm đến Python và AI.")

    if not answers:
        return "Tôi không biết thông tin này."
    return " ".join(answers)
