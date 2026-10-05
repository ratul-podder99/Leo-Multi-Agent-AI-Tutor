from orchestrator import Leo
import memory

leo = Leo()
profile = memory.load_profile("Test")

plan = leo.plan(profile, "Python decorators", "beginner")
if not plan.is_clear:
    print(plan.clarifying_question)
    raise SystemExit

explanation, quiz = leo.teach(plan, profile)
print("\n--- LESSON ---\n", explanation)

chosen = {}
for q in quiz.questions:
    print(f"\nQ{q.id}. {q.question}")
    for i, opt in enumerate(q.options, 1):
        print(f"  {i}) {opt}")
    chosen[q.id] = int(input("Your answer (1-4): ")) - 1

evaluation, score, weak = leo.grade(profile, plan, quiz, chosen)
print(f"\nScore: {int(score * 100)}%\n{evaluation.overall_feedback}")
for r in evaluation.results:
    print(f"Q{r.id}: {'✅' if r.is_correct else '❌'} {r.feedback}")