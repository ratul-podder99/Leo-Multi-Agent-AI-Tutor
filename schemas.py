from typing import List
from pydantic import BaseModel, Field


class Plan(BaseModel):
    """Coordinator output."""
    is_clear: bool
    clarifying_question: str = ""
    topic: str = ""
    level: str = "beginner"
    subtopics: List[str] = Field(default_factory=list)
    teaching_notes: str = ""


class Question(BaseModel):
    """One quiz question (Quiz Master output)."""
    id: int
    question: str
    options: List[str]          # exactly 4
    correct_index: int          # 0-3
    concept: str                # which subtopic it tests


class Quiz(BaseModel):
    topic: str
    questions: List[Question]


class QuestionResult(BaseModel):
    """Evaluator output per question."""
    id: int
    is_correct: bool
    feedback: str


class Evaluation(BaseModel):
    results: List[QuestionResult]
    overall_feedback: str
    weak_concepts: List[str] = Field(default_factory=list)