import json
import os

PATH = "student_memory.json"


def _load_all() -> dict:
    if not os.path.exists(PATH):
        return {}
    try:
        with open(PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def load_profile(name: str) -> dict:
    key = name.strip().lower()
    data = _load_all()
    return data.get(key, {"name": name.strip(), "sessions": [], "weak_concepts": []})


def save_profile(profile: dict) -> None:
    data = _load_all()
    data[profile["name"].strip().lower()] = profile
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def record_session(profile: dict, topic: str, score: float, weak: list) -> None:
    profile["sessions"].append({"topic": topic, "score": round(score, 2)})
    # keep a running list of concepts the student struggles with
    known = set(profile.get("weak_concepts", []))
    known.update(weak)
    if score >= 0.8:  # strong result: forget weak spots from this topic
        known.difference_update(weak)
    profile["weak_concepts"] = sorted(known)
    save_profile(profile)


def summary(profile: dict) -> str:
    """Short text injected into prompts."""
    if not profile["sessions"]:
        return "New student, no history yet."
    last = profile["sessions"][-3:]
    past = "; ".join(f"{s['topic']} ({int(s['score'] * 100)}%)" for s in last)
    weak = ", ".join(profile.get("weak_concepts", [])) or "none recorded"
    return f"Returning student. Recent sessions: {past}. Past weak concepts: {weak}."