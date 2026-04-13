from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from health.audit_engine import AUDIT_QUESTIONS, compute_scores
from health.models import HealthSelfAuditResult


def index(request):
    """
    Multi-step self-audit:
    - screen "select": show mode selector
    - screen "quiz": show one question at a time and store answers in session
    """

    # session storage for answers
    session_key = "health_self_audit_answers"

    mode = request.GET.get("mode") or request.POST.get("mode") or ""
    action = request.POST.get("action")  # "next" | "back" | "finish"
    raw_step = request.GET.get("step") or request.POST.get("step") or "1"
    try:
        step = int(raw_step)
    except ValueError:
        step = 1

    if mode != "self":
        # Starting over when user comes to /health without selecting the quiz.
        request.session.pop(session_key, None)
        return render(
            request,
            "health/index.html",
            {"screen": "select", "error": None},
        )

    # Ensure step in [1..20]
    step = max(1, min(step, 20))

    answers = request.session.get(session_key, {})
    request.session[session_key] = answers

    # GET screen
    if request.method == "GET":
        question = AUDIT_QUESTIONS[step - 1]
        return render(
            request,
            "health/index.html",
            {
                "screen": "quiz",
                "step": step,
                "total_steps": 20,
                "question": question,
                "selected_option_id": (
                    answers.get(f"q{question.number}")
                    if question.number != 20
                    else None
                ),
                "selected_q20_text": answers.get("q20_text", ""),
                "error": None,
            },
        )

    # POST screen: action handling
    # Keep answers even when moving back.
    error = None

    question = AUDIT_QUESTIONS[step - 1]
    if action == "back":
        # do not validate current answer
        next_step = max(1, step - 1)
        request.session.modified = True
        return redirect(f"{reverse('health_index')}?mode=self&step={next_step}")

    # next/finish: validate & store answer for current step
    if question.number == 20:
        submitted_text = (request.POST.get("q20_text") or "").strip()
        if not submitted_text:
            error = "Заполните поле ответа для вопроса 20."
        else:
            answers["q20_text"] = submitted_text
            request.session.modified = True
            # Finalize
            # compute_scores validates that q1..q19 are present
            try:
                result = compute_scores(answers)
            except ValueError as exc:
                error = str(exc)
            else:
                res_obj = HealthSelfAuditResult.objects.create(
                    answers_json=answers,
                    result_json=result,
                    overall_index=result["overall_index"],
                    overall_zone=result["overall_zone"],
                    accuracy_percent=result["criteria"]["accuracy"]["score_percent"],
                    speed_percent=result["criteria"]["speed"]["score_percent"],
                    capacity_percent=result["criteria"]["capacity"]["score_percent"],
                    manageability_percent=result["criteria"]["manageability"][
                        "score_percent"
                    ],
                )
                request.session.pop(session_key, None)
                return redirect("health_result", result_id=res_obj.pk)
    else:
        option_id = request.POST.get(f"q{question.number}")
        if not option_id:
            error = f"Выберите вариант ответа для вопроса {question.number}."
        else:
            # Validate option_id early to show friendly error.
            try:
                question.get_option(option_id)
            except ValueError as exc:
                error = str(exc)
            else:
                answers[f"q{question.number}"] = option_id
                request.session.modified = True

    if error:
        # Re-render same step with existing selections.
        return render(
            request,
            "health/index.html",
            {
                "screen": "quiz",
                "step": step,
                "total_steps": 20,
                "question": question,
                "selected_option_id": (
                    answers.get(f"q{question.number}")
                    if question.number != 20
                    else None
                ),
                "selected_q20_text": answers.get("q20_text", ""),
                "error": error,
            },
        )

    # Successful "next": move to next step or finish
    if step < 20:
        next_step = step + 1
        return redirect(f"{reverse('health_index')}?mode=self&step={next_step}")
    # step==20 success is handled above (redirect to result)
    return redirect("health_index")


def result(request, result_id: int):
    res_obj = get_object_or_404(HealthSelfAuditResult, pk=result_id)

    return render(
        request,
        "health/result.html",
        {
            "result": res_obj,
            "computed": res_obj.result_json,
        },
    )
