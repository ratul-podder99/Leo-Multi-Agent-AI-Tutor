from crewai import Task
from schemas import Plan, Quiz, Evaluation
import prompts as P


def plan_task(agent, name, topic, level, profile):
    return Task(
        description=P.PLAN_TASK.format(name=name, topic=topic, level=level, profile=profile),
        expected_output=P.PLAN_EXPECTED,
        agent=agent,
        output_pydantic=Plan,
    )


def explain_task(agent, plan, name, style="normal", extra=""):
    return Task(
        description=P.EXPLAIN_TASK.format(
            name=name, topic=plan.topic, level=plan.level,
            subtopics=", ".join(plan.subtopics) or plan.topic,
            notes=plan.teaching_notes or "none", style=style, extra=extra,
        ),
        expected_output=P.EXPLAIN_EXPECTED,
        agent=agent,
    )


def quiz_task(agent, explain, plan, n=5, difficulty="medium"):
    # HANDOFF: Explainer -> Quiz Master through context=[explain]
    return Task(
        description=P.QUIZ_TASK.format(
            n=n, topic=plan.topic, difficulty=difficulty,
            subtopics=", ".join(plan.subtopics) or plan.topic,
        ),
        expected_output=P.QUIZ_EXPECTED,
        agent=agent,
        context=[explain],
        output_pydantic=Quiz,
    )


def evaluate_task(agent, name, topic, answers_block):
    # HANDOFF: Quiz Master's questions + student's answers -> Evaluator
    return Task(
        description=P.EVALUATE_TASK.format(name=name, topic=topic, answers_block=answers_block),
        expected_output=P.EVALUATE_EXPECTED,
        agent=agent,
        output_pydantic=Evaluation,
    )