import streamlit as st
from orchestrator import Leo
import memory

st.set_page_config(page_title="Leo: Multi-Agent AI Tutor", page_icon="🦁", layout="wide")

ICONS = {"Coordinator": "🧭", "Explainer": "👩‍🏫", "Quiz Master": "❓", "Evaluator": "📝"}

DEFAULTS = dict(stage="start", profile=None, plan=None, explanation="", quiz=None,
                evaluation=None, score=0.0, weak=[], rounds=0, qv=0,
                message="", log=[])
for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)
S = st.session_state


def run_with_status(title, fn):
    """Runs fn(leo) while showing which agent is doing what, live."""
    with st.status(title, expanded=True) as status:
        def emit(agent, msg):
            S.log.append((agent, msg))
            status.write(f"{ICONS.get(agent, '🤖')} **{agent}**: {msg}")
        result = fn(Leo(emit))
        status.update(label="Done", state="complete", expanded=False)
    return result


# ------------------------------ SIDEBAR ------------------------------
with st.sidebar:
    st.title("🦁 Leo")
    st.caption("A team of AI agents that teaches you.")
    name = st.text_input("Your name")
    topic = st.text_input("What do you want to learn?")
    level = st.selectbox("Your level", ["beginner", "intermediate", "advanced"])
    start = st.button("Start learning", type="primary", use_container_width=True)

    st.subheader("Agent activity log")
    if S.log:
        for agent, msg in S.log[-15:]:
            st.markdown(f"{ICONS.get(agent, '🤖')} **{agent}**: {msg}")
    else:
        st.caption("Nothing yet.")

    if S.profile and S.profile["sessions"]:
        st.subheader("Memory")
        st.caption(memory.summary(S.profile))

# ------------------------------ START ------------------------------
if start:
    if not name.strip():
        st.sidebar.error("Please enter your name.")
    else:
        for k, v in DEFAULTS.items():
            S[k] = v if not isinstance(v, list) else []
        S.profile = memory.load_profile(name)
        try:
            plan = run_with_status("Coordinator is planning...",
                                   lambda leo: leo.plan(S.profile, topic, level))
            if not plan.is_clear:
                S.message = plan.clarifying_question
            else:
                S.plan = plan
                S.explanation, S.quiz = run_with_status(
                    "Explainer and Quiz Master are working...",
                    lambda leo: leo.teach(plan, S.profile))
                S.stage = "learning"
        except Exception as e:
            st.error(f"Something went wrong: {e}. Please try again.")
        st.rerun()

# ------------------------------ MAIN ------------------------------
st.title("Leo: Multi-Agent AI Tutor")

if S.stage == "start":
    if S.message:
        st.warning(f"🧭 Coordinator: {S.message}")
    else:
        st.info("Enter your name and a topic in the sidebar, then press **Start learning**.")

elif S.stage == "learning":
    st.subheader(f"📘 Lesson: {S.plan.topic}")
    if S.rounds:
        st.caption(f"Re-teaching round {S.rounds}")
    st.markdown(S.explanation)

    # Human-in-the-loop: student intervenes mid-run
    if st.button("🙋 Not clear, explain it simpler"):
        try:
            S.explanation, S.quiz = run_with_status(
                "Explainer is simplifying...",
                lambda leo: leo.teach(S.plan, S.profile, style="very simple, for a total beginner"))
            S.qv += 1
        except Exception as e:
            st.error(f"Could not simplify: {e}")
        st.rerun()

    st.divider()
    st.subheader("❓ Quiz")
    with st.form(f"quiz_form_{S.rounds}_{S.qv}"):
        picks = {}
        for q in S.quiz.questions:
            picks[q.id] = st.radio(f"Q{q.id}. {q.question}", q.options, index=None,
                                   key=f"q_{S.rounds}_{S.qv}_{q.id}")
        submitted = st.form_submit_button("Submit answers", type="primary")

    if submitted:
        if any(v is None for v in picks.values()):
            st.warning("Please answer every question.")
        else:
            chosen = {q.id: q.options.index(picks[q.id]) for q in S.quiz.questions}
            try:
                S.evaluation, S.score, S.weak = run_with_status(
                    "Evaluator is checking your answers...",
                    lambda leo: leo.grade(S.profile, S.plan, S.quiz, chosen))
                S.stage = "result"
            except Exception as e:
                st.error(f"Grading failed: {e}")
            st.rerun()

elif S.stage == "result":
    st.subheader("📝 Results")
    st.metric("Score", f"{int(S.score * 100)}%")
    st.info(S.evaluation.overall_feedback)

    by_id = {r.id: r for r in S.evaluation.results}
    for q in S.quiz.questions:
        r = by_id[q.id]
        with st.expander(f"{'✅' if r.is_correct else '❌'} Q{q.id}. {q.question}"):
            st.write(f"**Correct answer:** {q.options[q.correct_index]}")
            st.write(r.feedback)

    leo_check = Leo.needs_reteach(S.score, S.weak, S.rounds)
    if leo_check:
        st.warning(f"Weak areas: {', '.join(S.weak)}. Leo can re-teach them.")
        if st.button("🔁 Re-teach my weak areas", type="primary"):
            try:
                S.explanation, S.quiz = run_with_status(
                    "Feedback loop: Evaluator → Explainer → Quiz Master...",
                    lambda leo: leo.teach(S.plan, S.profile, focus=S.weak, n=3))
                S.rounds += 1
                S.stage = "learning"
            except Exception as e:
                st.error(f"Could not re-teach: {e}")
            st.rerun()
    elif S.score >= 0.6:
        st.success("Nice work! 🎉 Start a new topic from the sidebar.")
    else:
        st.info("Maximum re-teaching rounds reached. Try a new topic or restart this one.")