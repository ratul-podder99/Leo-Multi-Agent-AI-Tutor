from crewai import Crew, Process

import agents as A
import tasks as T
import memory
from schemas import Plan, Evaluation, QuestionResult

PASS_MARK = 0.6          # below this -> weak -> re-teach
MAX_RELEARN_ROUNDS = 2   # feedback loop cap
VAGUE = {"", "help", "help me", "stuff", "anything", "something", "study", "idk", "?"}


class Leo:
    def __init__(self, emit=None):
        # emit(agent_name, message) tells the UI who is doing what
        self.emit = emit or (lambda agent, msg: print(f"[{agent}] {msg}"))

    # ---------- safe runner: retries + validation ----------
    def _run(self, label, build, validate, retries=2):
        last_err = None
        for attempt in range(1, retries + 2):
            try:
                agents, tasks = build()          # rebuild fresh each attempt
                Crew(agents=agents, tasks=tasks,
                     process=Process.sequential, verbose=False).kickoff()
                validate(tasks)
                return tasks
            except Exception as e:
                last_err = e
                self.emit("Coordinator",
                          f"{label} hit a problem (attempt {attempt}): "
                          f"{type(e).__name__}. Retrying...")
        raise RuntimeError(f"{label} failed after {retries + 1} attempts: {last_err}")

    # ---------- stage 0: Coordinator ----------
    def plan(self, profile: dict, topic: str, level: str) -> Plan:
        topic = topic.strip()
        if topic.lower() in VAGUE or len(topic) < 3:
            self.emit("Coordinator", "Request is too vague, asking the student to clarify.")
            return Plan(is_clear=False, clarifying_question=(
                "What exactly would you like to learn? For example: "
                "'Python decorators' or 'How photosynthesis works'."))

        self.emit("Coordinator", "Reading your request and drafting a lesson plan...")
        prof = memory.summary(profile)

        def build():
            c = A.make_coordinator(prof)
            t = T.plan_task(c, profile["name"], topic, level, prof)
            return [c], [t]

        def validate(tasks):
            if tasks[0].output is None or tasks[0].output.pydantic is None:
                raise ValueError("no structured plan")

        try:
            tasks = self._run("Planning", build, validate)
            plan = tasks[0].output.pydantic
        except Exception:
            self.emit("Coordinator", "Planning failed, using a simple default plan.")
            plan = Plan(is_clear=True, topic=topic, level=level, subtopics=[topic])

        if plan.is_clear:
            self.emit("Coordinator",
                      f"Plan ready ({', '.join(plan.subtopics)}). Handing over to the Explainer.")
        return plan

    # ---------- stage 1: Explainer -> Quiz Master ----------
    def teach(self, plan: Plan, profile: dict, style="normal",
              focus=None, n=5, difficulty="medium"):
        prof = memory.summary(profile)
        extra = ""
        if focus:  # feedback loop: re-teach only the weak concepts
            extra = (f"The student struggled with: {', '.join(focus)}. "
                     "Teach ONLY these ideas, from a NEW angle, with a different analogy.")
            self.emit("Coordinator", f"Sending weak areas back to the Explainer: {', '.join(focus)}")

        self.emit("Explainer", "Writing the lesson..." if not focus else "Re-teaching weak areas...")

        def build():
            ex = A.make_explainer(prof)
            qm = A.make_quiz_master()
            t1 = T.explain_task(ex, plan, profile["name"], style, extra)
            t2 = T.quiz_task(qm, t1, plan, n, difficulty)
            return [ex, qm], [t1, t2]

        def validate(tasks):
            q = tasks[1].output.pydantic if tasks[1].output else None
            if q is None or not q.questions:
                raise ValueError("invalid quiz")
            for ques in q.questions:
                if len(ques.options) != 4 or not (0 <= ques.correct_index <= 3):
                    raise ValueError("malformed question")

        tasks = self._run("Lesson + quiz", build, validate)
        self.emit("Quiz Master", f"Received the lesson, built {n} questions.")
        return tasks[0].output.raw, tasks[1].output.pydantic

    # ---------- stage 2: Evaluator ----------
    def grade(self, profile: dict, plan: Plan, quiz, chosen: dict):
        """chosen = {question_id: chosen_option_index}"""
        prof = memory.summary(profile)
        self.emit("Evaluator", "Received the questions and your answers. Checking...")

        lines = []
        for q in quiz.questions:
            lines.append(
                f"Q{q.id} [{q.concept}]: {q.question}\n"
                f"  Correct answer: {q.options[q.correct_index]}\n"
                f"  Student answered: {q.options[chosen[q.id]]}"
            )
        block = "\n".join(lines)

        def build():
            ev = A.make_evaluator(prof)
            return [ev], [T.evaluate_task(ev, profile["name"], plan.topic, block)]

        def validate(tasks):
            if tasks[0].output is None or tasks[0].output.pydantic is None:
                raise ValueError("no evaluation")

        # Python is the source of truth for correctness (LLMs can mis-mark).
        truth = {q.id: chosen[q.id] == q.correct_index for q in quiz.questions}

        try:
            tasks = self._run("Evaluation", build, validate)
            ev = tasks[0].output.pydantic
            by_id = {r.id: r for r in ev.results}
        except Exception:
            self.emit("Coordinator", "Evaluator stalled, using a simple fallback review.")
            ev = Evaluation(results=[], overall_feedback="I couldn't generate detailed "
                            "feedback this time, but your score is below.")
            by_id = {}

        results = []
        for q in quiz.questions:
            r = by_id.get(q.id) or QuestionResult(
                id=q.id, is_correct=truth[q.id],
                feedback=("Correct!" if truth[q.id]
                          else f"The right answer is: {q.options[q.correct_index]}"))
            r.is_correct = truth[q.id]
            results.append(r)
        ev.results = results

        score = sum(truth.values()) / len(quiz.questions)
        weak = sorted({q.concept for q in quiz.questions if not truth[q.id]})
        ev.weak_concepts = weak

        memory.record_session(profile, plan.topic, score, weak)
        self.emit("Evaluator", f"Score {int(score * 100)}%. Weak concepts: {', '.join(weak) or 'none'}.")
        return ev, score, weak

    @staticmethod
    def needs_reteach(score: float, weak: list, rounds: int) -> bool:
        return score < PASS_MARK and bool(weak) and rounds < MAX_RELEARN_ROUNDS