from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


CRITICAL_THRESHOLDS: Tuple[int, int] = (49, 79)


def score_to_zone(score_percent: int) -> str:
    """
    Convert score to zone name (prototype colours).

    - 0..49 => "red"
    - 50..79 => "yellow"
    - 80..100 => "green"
    """
    if score_percent <= CRITICAL_THRESHOLDS[0]:
        return "red"
    if score_percent <= CRITICAL_THRESHOLDS[1]:
        return "yellow"
    return "green"


def _round_int(value: float) -> int:
    # Python round uses bankers rounding; for UI we want predictable "usual" rounding.
    return int(value + 0.5)


@dataclass(frozen=True)
class AuditOption:
    option_id: str
    label: str
    ball_percent: int


@dataclass(frozen=True)
class AuditQuestion:
    number: int
    title: str
    weight: int
    criterion: Optional[str]  # None for Q20 (open text)
    check_note: str
    impact_text: Optional[str] = None
    options: Optional[List[AuditOption]] = None

    def is_scored(self) -> bool:
        return self.options is not None and self.weight > 0

    def get_option(self, option_id: str) -> AuditOption:
        if not self.options:
            raise ValueError(f"Question {self.number} has no options.")
        for opt in self.options:
            if opt.option_id == option_id:
                return opt
        raise ValueError(f"Unknown option_id={option_id} for question {self.number}.")


AUDIT_QUESTIONS: List[AuditQuestion] = [
    AuditQuestion(
        number=1,
        title="Знаете ли точное число свободных ячеек?",
        weight=2,
        criterion="capacity",
        check_note="Проверяем: адресное хранение и контроль остатков.",
        options=[
            AuditOption("q1_opt1", "Да, в любой момент смотрю в системе", 100),
            AuditOption("q1_opt2", "Примерно знаю (±20%)", 67),
            AuditOption("q1_opt3", "Нет, нужно идти и смотреть", 33),
            AuditOption("q1_opt4", "Не знаю совсем", 0),
        ],
    ),
    AuditQuestion(
        number=2,
        title="Бывает ли, что товар «потерялся» на складе, а потом нашёлся через месяц?",
        weight=3,
        criterion="accuracy",
        check_note="Проверяем: точность учёта и ликвидность запасов.",
        impact_text="→ Потери денег + рекламации.",
        options=[
            AuditOption("q2_opt1", "Никогда", 100),
            AuditOption("q2_opt2", "Редко (1–2 раза в год)", 67),
            AuditOption("q2_opt3", "Часто (раз в месяц)", 33),
            AuditOption("q2_opt4", "Это норма нашей работы", 0),
        ],
    ),
    AuditQuestion(
        number=3,
        title="Сколько времени в среднем кладовщик ищет нужный товар?",
        weight=2,
        criterion="speed",
        check_note="Проверяем: система адресации и навигация.",
        options=[
            AuditOption("q3_opt1", "Меньше 1 минуты", 100),
            AuditOption("q3_opt2", "1–3 минуты", 67),
            AuditOption("q3_opt3", "3–10 минут", 33),
            AuditOption("q3_opt4", "Больше 10 минут / ходит и спрашивает других", 0),
        ],
    ),
    AuditQuestion(
        number=4,
        title="Приходилось ли отгружать клиенту не тот товар или не то количество за последний месяц?",
        weight=3,
        criterion="accuracy",
        check_note="Проверяем: точность комплектации.",
        impact_text="→ Возвраты, повторная доставка, сгоревшая маржа.",
        options=[
            AuditOption("q4_opt1", "Нет", 100),
            AuditOption("q4_opt2", "1–2 раза", 67),
            AuditOption("q4_opt3", "3–5 раз", 33),
            AuditOption("q4_opt4", "Больше 5 раз", 0),
        ],
    ),
    AuditQuestion(
        number=5,
        title="Есть ли у вас зоны / стеллажи, где товар стоит более полугода без движения?",
        weight=3,
        criterion="capacity",
        check_note="Проверяем: неликвиды и замороженный капитал.",
        impact_text="→ Замороженный капитал.",
        options=[
            AuditOption("q5_opt1", "Нет, всё идёт", 100),
            AuditOption("q5_opt2", "Да, до 10% площади", 67),
            AuditOption("q5_opt3", "Да, 10–30%", 33),
            AuditOption("q5_opt4", "Да, больше 30%", 0),
        ],
    ),
    AuditQuestion(
        number=6,
        title="Как часто поставщик привозит товар с ошибками (недовоз, пересорт, брак)?",
        weight=2,
        criterion="accuracy",
        check_note="Проверяем: качество входного контроля.",
        options=[
            AuditOption("q6_opt1", "Почти никогда", 100),
            AuditOption("q6_opt2", "Редко (раз в 2–3 месяца)", 67),
            AuditOption("q6_opt3", "Часто (раз в 1–2 недели)", 33),
            AuditOption("q6_opt4", "Каждая вторая поставка", 0),
        ],
    ),
    AuditQuestion(
        number=7,
        title="Бывают ли ситуации, когда товар приехал, а положить некуда (все ячейки заняты)?",
        weight=2,
        criterion="capacity",
        check_note="Проверяем: переполнение и неправильное зонирование.",
        options=[
            AuditOption("q7_opt1", "Никогда", 100),
            AuditOption("q7_opt2", "Редко", 67),
            AuditOption("q7_opt3", "Часто", 33),
            AuditOption("q7_opt4", "Постоянно, ставим в проходы", 0),
        ],
    ),
    AuditQuestion(
        number=8,
        title="Ваши кладовщики работают по бумажным спискам или со сканерами / голосом?",
        weight=1,
        criterion="speed",
        check_note="Проверяем: уровень автоматизации и скорость ошибок.",
        options=[
            AuditOption("q8_opt1", "Сканеры / терминалы сбора данных", 100),
            AuditOption("q8_opt2", "Голосовая отборка", 100),
            AuditOption("q8_opt3", "Бумажные списки", 33),
            AuditOption("q8_opt4", "По памяти", 0),
        ],
    ),
    AuditQuestion(
        number=9,
        title="Бывает ли, что машина под отгрузку уже приехала, а товар ещё не собран?",
        weight=2,
        criterion="speed",
        check_note="Проверяем: синхронизация отборки и отгрузки.",
        options=[
            AuditOption("q9_opt1", "Нет, всё готово заранее", 100),
            AuditOption("q9_opt2", "Редко (до 10% машин ждут)", 67),
            AuditOption("q9_opt3", "Часто (20–50%)", 33),
            AuditOption("q9_opt4", "Почти всегда", 0),
        ],
    ),
    AuditQuestion(
        number=10,
        title="Сколько времени в среднем занимает обработка одного возврата от клиента?",
        weight=2,
        criterion="speed",
        check_note="Проверяем: обратная логистика — скрытые потери.",
        options=[
            AuditOption("q10_opt1", "Меньше 1 дня", 100),
            AuditOption("q10_opt2", "1–3 дня", 67),
            AuditOption("q10_opt3", "3–7 дней", 33),
            AuditOption("q10_opt4", "Больше недели или не считаем", 0),
        ],
    ),
    AuditQuestion(
        number=11,
        title="Часто ли кладовщики работают сверхурочно именно из-за того, что «не успели за смену»?",
        weight=1,
        criterion="manageability",
        check_note="Проверяем: нормирование и планирование труда.",
        options=[
            AuditOption("q11_opt1", "Почти никогда", 100),
            AuditOption("q11_opt2", "Раз в неделю", 67),
            AuditOption("q11_opt3", "Несколько раз в неделю", 33),
            AuditOption("q11_opt4", "Почти каждый день", 0),
        ],
    ),
    AuditQuestion(
        number=12,
        title="Есть ли у вас чёткая разметка на полу (проходы, зоны, места для паллет)?",
        weight=1,
        criterion="manageability",
        check_note="Проверяем: безопасность и организация пространства.",
        options=[
            AuditOption("q12_opt1", "Да, всё размечено и соблюдается", 100),
            AuditOption("q12_opt2", "Разметка есть, но её не соблюдают", 50),
            AuditOption("q12_opt3", "Разметка частичная", 25),
            AuditOption("q12_opt4", "Нет никакой разметки", 0),
        ],
    ),
    AuditQuestion(
        number=13,
        title="Может ли новый сотрудник эффективно работать после 1 дня обучения?",
        weight=1,
        criterion="manageability",
        check_note="Проверяем: стандартизация процессов.",
        options=[
            AuditOption("q13_opt1", "Да, всё понятно", 100),
            AuditOption("q13_opt2", "Через 2–3 дня", 67),
            AuditOption("q13_opt3", "Только через неделю", 33),
            AuditOption("q13_opt4", "Месяц учится и ошибается", 0),
        ],
    ),
    AuditQuestion(
        number=14,
        title="Как часто товар повреждается при хранении или перемещении по складу?",
        weight=3,
        criterion="accuracy",
        check_note="Проверяем: эргономика и условия хранения.",
        impact_text="→ Потеря денег + рекламации.",
        options=[
            AuditOption("q14_opt1", "Почти никогда", 100),
            AuditOption("q14_opt2", "Редко (1–2 случая в месяц)", 67),
            AuditOption("q14_opt3", "Каждую неделю", 33),
            AuditOption("q14_opt4", "Каждый день", 0),
        ],
    ),
    AuditQuestion(
        number=15,
        title="Используете ли вы ABC-анализ (частые товары ближе к отгрузке, редкие — дальше)?",
        weight=2,
        criterion="speed",
        check_note="Проверяем: оптимизация маршрутов отбора.",
        options=[
            AuditOption("q15_opt1", "Да, и регулярно пересматриваем", 100),
            AuditOption("q15_opt2", "Да, но делали давно", 67),
            AuditOption("q15_opt3", "Частично, интуитивно", 33),
            AuditOption("q15_opt4", "Нет, все товары на одинаковых местах", 0),
        ],
    ),
    AuditQuestion(
        number=16,
        title="Бывает ли, что один и тот же товар хранится в 3–4 разных местах на складе?",
        weight=2,
        criterion="accuracy",
        check_note="Проверяем: дисциплина размещения (один SKU — одна зона).",
        options=[
            AuditOption("q16_opt1", "Нет, строго одно место", 100),
            AuditOption("q16_opt2", "Иногда, но редко", 67),
            AuditOption("q16_opt3", "Часто, так удобнее докладывать", 33),
            AuditOption("q16_opt4", "Да, это хаос", 0),
        ],
    ),
    AuditQuestion(
        number=17,
        title="Как вы проверяете, что заказ собран правильно, перед упаковкой?",
        weight=3,
        criterion="accuracy",
        check_note="Проверяем: качество контроля.",
        impact_text="→ Ошибки на этапе упаковки и лишние проверки.",
        options=[
            AuditOption("q17_opt1", "Сканируем каждый штрихкод", 100),
            AuditOption("q17_opt2", "Взвешиваем заказ", 80),
            AuditOption("q17_opt3", "Визуально сверяем с накладной", 40),
            AuditOption("q17_opt4", "Не проверяем, доверяем кладовщику", 0),
        ],
    ),
    AuditQuestion(
        number=18,
        title="Знают ли кладовщики свою выработку (строк/час, ошибки, время простоя)?",
        weight=1,
        criterion="manageability",
        check_note="Проверяем: мотивация и управление эффективностью.",
        options=[
            AuditOption("q18_opt1", "Да, у нас KPI и он влияет на оплату", 100),
            AuditOption("q18_opt2", "Да, но не влияет на зарплату", 67),
            AuditOption("q18_opt3", "Начальник знает, они — нет", 33),
            AuditOption("q18_opt4", "Никто не считает", 0),
        ],
    ),
    AuditQuestion(
        number=19,
        title="Бывают ли конфликты между приёмкой и отгрузкой за одни и те же ресурсы (люди, техника, проходы)?",
        weight=2,
        criterion="speed",
        check_note="Проверяем: потоковый баланс (теория ограничений).",
        options=[
            AuditOption("q19_opt1", "Нет, всё разделено", 100),
            AuditOption("q19_opt2", "Редко", 67),
            AuditOption("q19_opt3", "Часто", 33),
            AuditOption("q19_opt4", "Постоянно, это узкое горлышко", 0),
        ],
    ),
    AuditQuestion(
        number=20,
        title="Что исправили бы за 1 день (открытый ответ)?",
        weight=0,
        criterion=None,
        check_note="Используется для формирования блока «Быстрые победы».",
        options=None,
    ),
]

QUESTION_BY_NUMBER: Dict[int, AuditQuestion] = {q.number: q for q in AUDIT_QUESTIONS}


def _score_weighted_average(
    items: List[Tuple[int, int]],
    *,
    default: int = 0,
) -> int:
    """
    items = [(ball_percent, weight), ...]
    returns integer percent using weighted average
    """
    weight_sum = sum(w for _, w in items)
    if weight_sum <= 0:
        return default
    weighted = sum(ball * w for ball, w in items) / weight_sum
    return _round_int(weighted)


def compute_scores(answers: Dict[str, Any]) -> Dict[str, Any]:
    """
    answers:
      - q1..q19: selected option_id strings
      - q20_text: free text (optional)
    """
    # Total score uses only questions with answers and options (Q20 doesn't affect).
    scored_questions = [q for q in AUDIT_QUESTIONS if q.is_scored()]

    # Validate required answers.
    selected_option_ids: Dict[int, str] = {}
    for q in scored_questions:
        key = f"q{q.number}"
        option_id = answers.get(key)
        if not option_id or not isinstance(option_id, str):
            raise ValueError(f"Missing required answer for {key}.")
        # Validate option.
        selected_option_ids[q.number] = option_id
        _ = q.get_option(option_id)  # will raise if invalid

    # Total
    total_items: List[Tuple[int, int]] = []
    for q in scored_questions:
        opt = q.get_option(selected_option_ids[q.number])
        total_items.append((opt.ball_percent, q.weight))

    total_score = _score_weighted_average(total_items, default=0)
    total_zone = score_to_zone(total_score)

    # Criteria
    criteria_keys = ["accuracy", "speed", "capacity", "manageability"]
    criteria_scores: Dict[str, Dict[str, Any]] = {}
    for crit in criteria_keys:
        crit_items: List[Tuple[int, int]] = []
        for q in scored_questions:
            if q.criterion == crit:
                opt = q.get_option(selected_option_ids[q.number])
                crit_items.append((opt.ball_percent, q.weight))
        crit_score = _score_weighted_average(crit_items, default=0)
        criteria_scores[crit] = {
            "score_percent": crit_score,
            "zone": score_to_zone(crit_score),
        }

    # Top-3 gaps: among weight=3 questions, take 3 lowest ball_percent.
    weight3_questions = [q for q in scored_questions if q.weight == 3]
    gap_candidates: List[Tuple[int, int, str]] = (
        []
    )  # (ball, question_number, option_id)
    for q in weight3_questions:
        opt = q.get_option(selected_option_ids[q.number])
        gap_candidates.append((opt.ball_percent, q.number, opt.option_id))
    gap_candidates.sort(key=lambda t: (t[0], t[1]))
    top3 = gap_candidates[:3]

    top_gaps: List[Dict[str, Any]] = []
    for ball, q_number, _opt_id in top3:
        q = QUESTION_BY_NUMBER[q_number]
        opt = q.get_option(selected_option_ids[q_number])
        top_gaps.append(
            {
                "question_number": q_number,
                "title": q.title,
                "selected_label": opt.label,
                "check_note": q.check_note,
                "impact_text": q.impact_text,
            }
        )

    # Quick wins from Q20
    q20_text = answers.get("q20_text") or ""
    q20_text = str(q20_text).strip()

    return {
        "overall_index": total_score,
        "overall_zone": total_zone,
        "criteria": criteria_scores,
        "top_gaps": top_gaps,
        "quick_win_quote": q20_text,
    }
