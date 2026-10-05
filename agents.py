from crewai import Agent
from llm import get_llm
import prompts as P


def _agent(role, goal, backstory, temperature=0.4):
    return Agent(
        role=role,
        goal=goal,
        backstory=backstory,
        llm=get_llm(temperature),
        allow_delegation=False,
        verbose=False,
        max_iter=3,                # stops runaway loops
        max_execution_time=120,    # seconds, stops stalls
    )


def make_coordinator(profile: str) -> Agent:
    return _agent("Coordinator", P.COORDINATOR_GOAL,
                  P.COORDINATOR_BACKSTORY.format(profile=profile), 0.2)


def make_explainer(profile: str) -> Agent:
    return _agent("Explainer", P.EXPLAINER_GOAL,
                  P.EXPLAINER_BACKSTORY.format(profile=profile), 0.6)


def make_quiz_master() -> Agent:
    return _agent("Quiz Master", P.QUIZ_GOAL, P.QUIZ_BACKSTORY, 0.4)


def make_evaluator(profile: str) -> Agent:
    return _agent("Evaluator", P.EVALUATOR_GOAL,
                  P.EVALUATOR_BACKSTORY.format(profile=profile), 0.2)