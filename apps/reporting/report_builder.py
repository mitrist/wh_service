from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List

from apps.calculations.score import QUESTION_BY_NUMBER

if TYPE_CHECKING:
    from apps.core.models import AuditSession


ZONE_META = {
    "green": {"emoji": "🟢", "label": "Устойчиво", "ui_label": "Норма / точки роста"},
    "yellow": {"emoji": "🟡", "label": "Есть резервы", "ui_label": "Системные риски"},
    "orange": {"emoji": "🟠", "label": "Системные проблемы", "ui_label": "Системные проблемы"},
    "red": {"emoji": "🔴", "label": "Критическая зона", "ui_label": "Критично"},
}

INDEX_BANDS = [
    {
        "min": 80,
        "max": 100,
        "emoji": "🟢",
        "title": "Склад работает устойчиво",
        "description": "Есть точки роста, системных потерь нет.",
        "zone": "green",
    },
    {
        "min": 60,
        "max": 79,
        "emoji": "🟡",
        "title": "Есть зоны риска",
        "description": "Несколько зон тянут результат вниз. Потери реальные, но управляемые.",
        "zone": "yellow",
    },
    {
        "min": 40,
        "max": 59,
        "emoji": "🟠",
        "title": "Системные проблемы",
        "description": "Системные проблемы в 2–3 зонах. Потери накапливаются ежедневно.",
        "zone": "orange",
    },
    {
        "min": 0,
        "max": 39,
        "emoji": "🔴",
        "title": "Критическая зона",
        "description": "Склад работает против бизнеса.",
        "zone": "red",
    },
]

CRITERIA_META = {
    "accuracy": {
        "title": "Точность",
        "emoji": "🎯",
        "measured": "Ошибки отгрузки, пересорт, входной контроль, контроль упаковки",
    },
    "speed": {
        "title": "Скорость",
        "emoji": "⚡",
        "measured": "Поиск товара, ожидание транспорта, обработка возвратов, ABC",
    },
    "capacity": {
        "title": "Ёмкость",
        "emoji": "📦",
        "measured": "Свободные ячейки, неликвиды, нехватка мест, дробление SKU",
    },
    "manageability": {
        "title": "Управляемость",
        "emoji": "🧠",
        "measured": "Инструменты отборки, разметка, стандарты, KPI, конфликты потоков",
    },
}

TOP_POINT_META = {
    "q17": {
        "market_norm": "Сканирование штрихкода или весовой контроль каждого заказа",
        "gap": "Отсутствует любой системный контроль",
        "why_costly": (
            "Без контроля перед упаковкой ошибки отгрузки неизбежны — это не вопрос "
            "внимательности людей, а вопрос архитектуры процесса."
        ),
        "check_now": [
            "Есть ли физическое место для контрольной операции перед упаковкой?",
            "Знают ли кладовщики, что именно они должны проверять?",
            "Ведётся ли журнал ошибок — хотя бы вручную?",
        ],
        "quick_solution": (
            "Ввести правило: перед упаковкой — сверка накладной с товаром и подпись кладовщика."
        ),
    },
    "q14": {
        "market_norm": "1–2 случая в месяц (склад до 500 SKU)",
        "gap": "Частота повреждений выше практики устойчивых складов",
        "why_costly": (
            "Повреждения — двойной удар: прямое списание плюс рекламации. "
            "На производственных складах это ещё и риск остановки линии."
        ),
        "check_now": [
            "Соответствуют ли стеллажи заявленной нагрузке?",
            "Есть ли инструкции по укладке хрупкого и тяжёлого товара?",
            "Проверялась ли квалификация водителей погрузчиков в последние 6 месяцев?",
            "Где именно происходят повреждения — при хранении или при перемещении?",
        ],
        "quick_solution": (
            "Пройти по складу и сфотографировать все места повреждений и деформированные стеллажи."
        ),
    },
    "q5": {
        "market_norm": "Менее 5% площади под неликвид",
        "gap": "Слишком много замороженной площади под товар без движения",
        "why_costly": (
            "Товар без движения — это замороженный капитал плюс стоимость хранения. "
            "Стоимость владения запасом обычно 20–30% в год."
        ),
        "check_now": [
            "Есть ли список товаров без движения >6 месяцев в учётной системе?",
            "Известна ли причина залёживания — избыточная закупка, брак, сезонность?",
            "Есть ли полномочия для списания или продажи по себестоимости?",
        ],
        "quick_solution": (
            "Выгрузить отчёт движения за 6 месяцев и отсортировать позиции по нулевому движению."
        ),
    },
}

BENCHMARK_ROWS = [
    {
        "title": "Ошибки отгрузки",
        "weak": ">1% строк",
        "average": "0,3–1%",
        "good": "<0,1%",
        "question": "q4",
    },
    {
        "title": "Время поиска товара",
        "weak": ">10 мин",
        "average": "3–10 мин",
        "good": "<1 мин",
        "question": "q3",
    },
    {
        "title": "Доля неликвидов",
        "weak": ">20% площади",
        "average": "10–20%",
        "good": "<5%",
        "question": "q5",
    },
    {
        "title": "Обработка возврата",
        "weak": ">7 дней",
        "average": "3–7 дней",
        "good": "<1 дня",
        "question": "q10",
    },
    {
        "title": "Ввод нового сотрудника",
        "weak": ">2 недель",
        "average": "3–7 дней",
        "good": "1–2 дня",
        "question": "q13",
    },
    {
        "title": "Машины, ожидающие товар",
        "weak": ">30%",
        "average": "10–30%",
        "good": "<5%",
        "question": "q9",
    },
]

LOSS_MAP = [
    {
        "title": "Прямые списания",
        "description": "Бой, пересорт, недостача. Видны сразу, но обычно занижены.",
    },
    {
        "title": "Скрытый ФОТ",
        "description": "Поиск товара, ожидание задания, переделка ошибок.",
    },
    {
        "title": "Замороженный капитал",
        "description": "Неликвиды и избыточные запасы. Деньги не работают.",
    },
    {
        "title": "Потери на клиентах",
        "description": "Возвраты, рекламации, потерянные повторные заказы.",
    },
    {
        "title": "Операционные потери",
        "description": "Простои производства из-за склада, срывы сроков, штрафы.",
    },
]


def _zone_from_score(score: int) -> str:
    if score >= 80:
        return "green"
    if score >= 60:
        return "yellow"
    if score >= 40:
        return "orange"
    return "red"


def _zone_tag(score: int) -> str:
    zone = _zone_from_score(score)
    meta = ZONE_META[zone]
    return f"{meta['emoji']} {meta['label']}"


def _get_index_band(score: int) -> Dict[str, Any]:
    for band in INDEX_BANDS:
        if band["min"] <= score <= band["max"]:
            return band
    return INDEX_BANDS[-1]


def _build_criteria(raw_scores: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for key, val in (raw_scores.get("criteria") or {}).items():
        score = int(val.get("score_percent") or 0)
        meta = CRITERIA_META.get(key, {"title": key, "emoji": "", "measured": ""})
        rows.append(
            {
                "key": key,
                "title": meta["title"],
                "emoji": meta["emoji"],
                "score_percent": score,
                "zone": _zone_from_score(score),
                "zone_label": _zone_tag(score),
                "measured": meta["measured"],
            },
        )
    return rows


def _problem_meta(question_code: str, fallback_title: str) -> Dict[str, Any]:
    default = {
        "market_norm": "Нужна детализация на очном аудите.",
        "gap": "Есть разрыв между текущим процессом и устойчивой практикой.",
        "why_costly": "Потери в этой точке накапливаются ежедневно и ухудшают управляемость.",
        "check_now": [
            "Кто отвечает за процесс по этой точке?",
            "Есть ли формализованный стандарт выполнения операции?",
            "Есть ли данные по частоте ошибок?",
        ],
        "quick_solution": "Зафиксировать текущий процесс и внедрить контрольную точку на 1 неделю.",
    }
    if question_code in TOP_POINT_META:
        return TOP_POINT_META[question_code]
    if "повреж" in fallback_title.lower():
        return TOP_POINT_META.get("q14", default)
    return default


def _build_top_points(raw_scores: Dict[str, Any], answers: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for idx, gap in enumerate(raw_scores.get("top_gaps") or [], start=1):
        n = gap["question_number"]
        code = f"q{n}"
        q = QUESTION_BY_NUMBER[n]
        opt_id = answers.get(code, "")
        selected_label = ""
        if opt_id:
            selected_label = q.get_option(opt_id).label
        meta = _problem_meta(code, gap.get("title") or "")
        rows.append(
            {
                "rank": idx,
                "severity_zone": _zone_from_score(int(gap.get("selected_score_percent", 0))),
                "question_code": code,
                "title": gap.get("title") or "",
                "selected_answer": selected_label or gap.get("selected_label") or "",
                "market_norm": meta["market_norm"],
                "gap": meta["gap"],
                "why_costly": meta["why_costly"],
                "check_now": meta["check_now"],
                "quick_solution": meta["quick_solution"],
                "risk_score": gap.get("risk_score"),
                "quick_fix": gap.get("quick_fix"),
                "limitation": gap.get("limitation"),
            },
        )
    return rows


def _benchmark_status(question_code: str, answers: Dict[str, Any]) -> str:
    opt_id = answers.get(question_code)
    if not opt_id:
        return "—"
    q = QUESTION_BY_NUMBER[int(question_code[1:])]
    score = q.get_option(opt_id).ball_percent
    if score >= 80:
        return "🟢"
    if score >= 50:
        return "🟡"
    if score >= 33:
        return "🟠"
    return "🔴"


def _build_market_benchmarks(answers: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for item in BENCHMARK_ROWS:
        rows.append(
            {
                "title": item["title"],
                "weak": item["weak"],
                "average": item["average"],
                "good": item["good"],
                "your_result": _benchmark_status(item["question"], answers),
            },
        )
    return rows


def _build_next_steps(overall_score: int, criteria_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    red_count = sum(1 for c in criteria_rows if c["zone"] in {"red", "orange"})
    highlight = "self_guided"
    if overall_score < 50 or red_count >= 2:
        highlight = "field_audit"
    elif red_count >= 1:
        highlight = "targeted_consulting"
    return {
        "highlight": highlight,
        "paths": [
            {
                "code": "self_guided",
                "title": "Разобраться самостоятельно",
                "description": "Подходит, если индекс выше 60% и проблемы точечные.",
            },
            {
                "code": "targeted_consulting",
                "title": "Точечная консультация",
                "description": "Подходит, если есть одна красная зона, но непонятны причины.",
            },
            {
                "code": "field_audit",
                "title": "Выездной аудит",
                "description": (
                    "Подходит, если индекс ниже 50% или нужны цифры для руководства. "
                    "Включает хронометраж, анализ учётной системы и расчёт потерь в рублях."
                ),
            },
        ],
    }


def build_full_report_payload(
    raw_scores: Dict[str, Any],
    answers: Dict[str, Any],
    session: "AuditSession",
) -> Dict[str, Any]:
    overall_score = int(raw_scores.get("overall_index") or 0)
    index_band = _get_index_band(overall_score)
    criteria_rows = _build_criteria(raw_scores)
    top_points = _build_top_points(raw_scores, answers)
    q20 = (answers.get("q20_text") or "").strip()

    return {
        "header": {
            "company": (session.client_company or "").strip() or "Без названия компании",
            "date": datetime.now().strftime("%d.%m.%Y"),
            "method": "Методика: выездной аудит складской логистики, 50+ предприятий",
            "disclaimer": [
                "Точность самодиагностики — около 60%. Отчёт показывает направления, не точные цифры.",
                "Для расчёта потерь в рублях нужен выездной аудит с хронометражем.",
            ],
        },
        "overall_index": {
            "score_percent": overall_score,
            "zone": index_band["zone"],
            "zone_label": f"{index_band['emoji']} {index_band['title']}",
            "description": index_band["description"],
            "formula_note": (
                "Итог = сумма (ответ × вес) / максимум × 100%. "
                "Вес 3: критичные ошибки; вес 2: скорость и синхронизация; вес 1: управленческие практики."
            ),
        },
        "criteria": {
            "rows": criteria_rows,
            "read_note": (
                "Критерий ниже 50% — зона активных потерь. 50–70% — есть резервы. "
                "Выше 70% — относительно устойчиво."
            ),
        },
        "top_loss_points": top_points,
        "market_benchmarks": {
            "rows": _build_market_benchmarks(answers),
            "note": "Бенчмарки собраны из практики выездных аудитов.",
        },
        "loss_map": {
            "items": LOSS_MAP,
            "note": (
                "Самоаудит показывает, где концентрируются потери. "
                "Точные цифры по каждой статье даёт только очный аудит."
            ),
        },
        "quick_wins": {
            "from_q20": q20,
            "personal_recommendation": (
                "Начните с самой повторяющейся операции из ответа и введите ежедневный короткий контроль результата."
            ),
            "yellow_zone_tip": (
                "Распечатайте схему склада и отметьте, где чаще всего теряется время. "
                "Это быстрый способ увидеть узкие места."
            ),
            "universal_tip": (
                "Проведите 15-минутный разбор с командой: «Что мешает работать быстрее?» "
                "Запишите ответы и назначьте владельцев задач."
            ),
        },
        "next_steps": _build_next_steps(overall_score, criteria_rows),
    }
