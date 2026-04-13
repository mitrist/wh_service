ПРОМТ-ТЕХНИЧЕСКОЕ ЗАДАНИЕ
Веб-сервис «Складской аудит: Self-Audit для заказчика»
1. Назначение сервиса
Сервис позволяет:

Заказчику (владельцу склада, логисту) самостоятельно пройти 20-вопросную анкету с весами и получить цветной диагностический отчёт (индекс здоровья, 4 критерия, топ-3 проблемы, быстрые победы).

Консультанту (автору алгоритма) проводить полный аудит по 38 вопросам (включая фото, комментарии, хронометраж), сохранять черновики, экспортировать результаты.

На первом этапе реализуется режим заказчика (self-audit).
Режим консультанта — второй этап.

2. Стек технологий
Компонент	Технология
Бэкенд	Python 3.11+, Django 5.0+, Django REST Framework (DRF)
База данных	PostgreSQL 15+ (продакшн), SQLite (разработка)
Миграции	Django Migrations
Аутентификация	Django REST Framework TokenAuth / JWT (опционально)
API документация	drf-spectacular (OpenAPI/Swagger)
Фоновые задачи	Celery + Redis (для генерации PDF-отчётов)
PDF-генерация	WeasyPrint или ReportLab
Логирование	Django logging + Sentry (опционально)
Переменные окружения	python-decouple или django-environ
Фронтенд (минимально)	Django Templates + HTMX + Bootstrap 5 (для быстрого MVP)
3. Модели данных (Django Models)
3.1. AuditSession — сессия прохождения анкеты
python
class AuditSession(models.Model):
    MODE_CHOICES = (
        ('self', 'Self-audit (заказчик)'),
        ('pro', 'Pro-аудит (консультант)'),
    )
    STATUS_CHOICES = (
        ('draft', 'Черновик'),
        ('completed', 'Завершён'),
        ('archived', 'В архиве'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mode = models.CharField(max_length=10, choices=MODE_CHOICES, default='self')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    
    # Клиентские данные (только для self-режима)
    client_name = models.CharField(max_length=200, blank=True)
    client_company = models.CharField(max_length=200, blank=True)
    client_email = models.EmailField()
    
    # Метаданные
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_modified = models.DateTimeField(auto_now=True)
    
    # Результаты расчётов (кэшируются при завершении)
    total_score = models.FloatField(null=True, blank=True)  # 0-100
    total_grade = models.CharField(max_length=10, null=True, blank=True)  # green/yellow/red
    
    class Meta:
        indexes = [
            models.Index(fields=['status', 'client_email']),
            models.Index(fields=['mode', 'completed_at']),
        ]
3.2. Question — вопросы (администрируются через Django Admin)
python
class Question(models.Model):
    CATEGORY_CHOICES = (
        ('accuracy', 'Точность'),
        ('speed', 'Скорость'),
        ('capacity', 'Ёмкость'),
        ('manageability', 'Управляемость'),
    )
    WEIGHT_CHOICES = ((1, 'Индикативный'), (2, 'Важный'), (3, 'Критический'))
    
    code = models.CharField(max_length=10, unique=True)  # q1, q2, ..., q20
    text = models.TextField()  # Текст вопроса
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    weight = models.IntegerField(choices=WEIGHT_CHOICES, default=1)
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_self_audit = models.BooleanField(default=True)  # Показывать в self-режиме
    
    # Описание для клиента (подсказка)
    hint = models.TextField(blank=True)
    
    class Meta:
        ordering = ['order']
3.3. AnswerOption — варианты ответов
python
class AnswerOption(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    text = models.CharField(max_length=500)  # Текст варианта
    score_percent = models.IntegerField()  # 0, 25, 33, 40, 50, 67, 80, 100
    order = models.PositiveSmallIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
        unique_together = [['question', 'order']]
3.4. UserAnswer — ответ пользователя в рамках сессии
python
class UserAnswer(models.Model):
    session = models.ForeignKey(AuditSession, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.ForeignKey(AnswerOption, on_delete=models.CASCADE, null=True, blank=True)
    open_answer_text = models.TextField(blank=True)  # Для вопроса 20
    
    # Для про-режима (фото, комментарий)
    comment = models.TextField(blank=True)
    photo = models.ImageField(upload_to='audit_photos/%Y/%m/%d/', null=True, blank=True)
    
    class Meta:
        unique_together = [['session', 'question']]
3.5. AuditReport — сгенерированный отчёт (PDF + метаданные)
python
def get_report_path(instance, filename):
    return f'reports/session_{instance.session.id}/{filename}'

class AuditReport(models.Model):
    session = models.OneToOneField(AuditSession, on_delete=models.CASCADE, related_name='report')
    pdf_file = models.FileField(upload_to=get_report_path)
    generated_at = models.DateTimeField(auto_now_add=True)
    
    # Кэшированные данные отчёта
    summary = models.JSONField(default=dict)  # {total_score, grade, category_scores, top_problems}
4. API Endpoints (Django REST Framework)
Базовый URL: /api/v1/

4.1. Публичные (без аутентификации)
Method	Endpoint	Описание
GET	/questions/self/	Список вопросов для self-аудита (20 шт) с вариантами ответов
POST	/sessions/	Создать новую сессию (started_at, status=draft)
GET	/sessions/{uuid}/	Получить сессию + все ответы
PATCH	/sessions/{uuid}/answers/	Обновить ответ на один вопрос (принимает question_code + option_id или open_answer_text)
POST	/sessions/{uuid}/complete/	Завершить сессию → запустить расчёт + генерацию PDF
GET	/sessions/{uuid}/report/	Скачать PDF-отчёт
4.2. Защищённые (токен, для консультанта — второй этап)
Method	Endpoint	Описание
GET	/questions/pro/	38 вопросов для про-аудита
POST	/sessions/pro/	Создать сессию в режиме консультанта
POST	/sessions/{uuid}/upload-photo/	Загрузить фото к вопросу
GET	/sessions/export/csv/	Экспорт всех сессий (фильтр по дате)
5. Логика расчёта результатов
5.1. Псевдокод (Python)
python
def calculate_session_result(session: AuditSession) -> dict:
    answers = session.answers.select_related('question', 'selected_option')
    
    # Словари для накопления
    category_weights = {}
    category_scores = {}
    top_problems = []  # (question, weight, score_percent)
    
    for answer in answers:
        q = answer.question
        if not answer.selected_option:
            continue
        
        score = answer.selected_option.score_percent / 100.0  # 0..1
        
        # Для топ-проблем: берём вопросы с weight=3 и score < 0.5
        if q.weight == 3 and score < 0.5:
            top_problems.append((q, q.weight, score))
        
        cat = q.category
        category_weights[cat] = category_weights.get(cat, 0) + q.weight
        category_scores[cat] = category_scores.get(cat, 0) + (score * q.weight)
    
    # Категорийные баллы (0-100%)
    category_results = {}
    for cat in category_weights:
        raw = (category_scores[cat] / category_weights[cat]) * 100
        category_results[cat] = round(raw, 1)
    
    # Общий балл (среднее по категориям с учётом весов категорий — или просто среднее)
    total_score = sum(category_results.values()) / len(category_results) if category_results else 0
    total_score = round(total_score, 1)
    
    # Оценка (зелёный/жёлтый/красный)
    if total_score >= 80:
        grade = 'green'
    elif total_score >= 50:
        grade = 'yellow'
    else:
        grade = 'red'
    
    # Топ-3 критических (сортируем по score, худшие сверху)
    top_problems.sort(key=lambda x: x[2])
    top_3 = [
        {
            'question_code': p[0].code,
            'question_text': p[0].text,
            'score_percent': int(p[2] * 100),
            'weight': p[1]
        }
        for p in top_problems[:3]
    ]
    
    return {
        'total_score': total_score,
        'grade': grade,
        'category_scores': category_results,
        'top_problems': top_3,
    }
5.2. Хранение результата
При вызове POST /sessions/{uuid}/complete/:

Выполняется расчёт.

Данные сохраняются в session.total_score и session.total_grade.

Запускается Celery-задача generate_pdf_report.delay(session.id).

Сессии присваивается status='completed' и completed_at=now().

Возвращается JSON с результатом (пока PDF генерируется асинхронно).

6. Генерация PDF-отчёта
Отчёт содержит (см. макет выше):

Шапка: название компании, дата, ID сессии.

Общий индекс здоровья (крупная шкала + процент).

Таблица 4 критериев с цветными индикаторами.

Топ-3 критических разрыва (вопрос, проблема, рекомендация — рекомендация формируется из предустановленных шаблонов по question.code).

Быстрые победы (из открытого ответа на вопрос 20).

CTA-блок (скачать PDF, записаться на аудит — статическая ссылка).

6.1. Рекомендации по шаблонам
Для каждого вопроса с weight=3 в админке задаётся recommendation_text (текст рекомендации).
В отчёт подтягивается автоматически.

Модель:

python
class Question(models.Model):
    # ... поля выше
    pro_recommendation = models.TextField(blank=True, help_text="Рекомендация для консультанта")
    self_recommendation = models.TextField(blank=True, help_text="Короткая рекомендация для заказчика в отчёте")
7. Django Admin интерфейс
Для управления контентом без программирования:

QuestionAdmin: список всех вопросов, фильтр по категории, весу, активности. Inline-редактирование вариантов ответов.

AnswerOptionInline: tabular inline.

AuditSessionAdmin: просмотр сессий, фильтр по статусу, режиму, дате. Кнопка «Сформировать отчёт заново».

AuditReportAdmin: просмотр сгенерированных PDF, возможность скачать.

8. Файловая структура проекта (рекомендуемая)
text
warehouse_audit/
├── manage.py
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   └── urls.py
├── apps/
│   ├── core/
│   │   ├── models.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   └── migrations/
│   ├── api/
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   └── permissions.py
│   ├── calculations/
│   │   ├── score.py
│   │   └── categories.py
│   ├── reporting/
│   │   ├── pdf_generator.py
│   │   ├── templates/
│   │   │   └── report_template.html
│   │   └── tasks.py (Celery)
│   └── frontend/
│       ├── templates/
│       │   ├── self_audit_form.html
│       │   ├── result_page.html
│       │   └── base.html
│       └── static/
│           └── css/
├── media/
│   ├── audit_photos/
│   └── reports/
├── static/
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
└── .env
9. Последовательность разработки (MVP для self-аудита)
Этап	Задача	Оценка (часы)
1	Настройка Django + DRF + PostgreSQL	2
2	Модели: Question, AnswerOption, AuditSession, UserAnswer	3
3	Админка: загрузка 20 вопросов + вариантов ответов	2
4	API: GET /questions/self/, POST /sessions/, PATCH /answers/	4
5	Логика расчёта (функция score.py)	3
6	API: POST /complete/ + вызов расчёта	2
7	PDF-генерация (WeasyPrint + HTML-шаблон)	5
8	Celery + Redis (асинхронная генерация PDF)	3
9	Простейший фронтенд (Django Templates + HTMX) — анкета в один шаг с сохранением прогресса	6
10	Страница результата (отображение JSON + ссылка на PDF)	2
11	Тестирование (Postman + unit-тесты на расчёт)	4
Итого		36 часов (~5 дней)
10. Пример JSON-запроса/ответа
10.1. Создание сессии
POST /api/v1/sessions/

json
{
  "mode": "self",
  "client_name": "Алексей",
  "client_company": "ООО Логист",
  "client_email": "alexey@logist.ru"
}
Ответ (201 Created):

json
{
  "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "mode": "self",
  "status": "draft",
  "started_at": "2026-04-11T10:00:00Z",
  "total_score": null
}
10.2. Сохранение ответа
PATCH /api/v1/sessions/f47ac10b-58cc-4372-a567-0e02b2c3d479/answers/

json
{
  "question_code": "q1",
  "option_id": 5
}
Или для открытого вопроса:

json
{
  "question_code": "q20",
  "open_answer_text": "Сделать нормальную навигацию по складу"
}
10.3. Завершение и результат
POST /api/v1/sessions/f47ac10b-58cc-4372-a567-0e02b2c3d479/complete/

Ответ (200 OK):

json
{
  "session_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "processing",
  "message": "Расчёт выполнен, PDF генерируется. Проверьте через 10 секунд.",
  "result": {
    "total_score": 48.2,
    "grade": "red",
    "category_scores": {
      "accuracy": 42.0,
      "speed": 58.0,
      "capacity": 51.0,
      "manageability": 39.0
    },
    "top_problems": [
      {
        "question_code": "q14",
        "question_text": "Как часто товар повреждается при хранении или перемещении?",
        "score_percent": 33,
        "weight": 3
      },
      {
        "question_code": "q4",
        "question_text": "Приходилось ли отгружать клиенту не тот товар за последний месяц?",
        "score_percent": 33,
        "weight": 3
      },
      {
        "question_code": "q5",
        "question_text": "Есть ли неликтив более 6 месяцев?",
        "score_percent": 33,
        "weight": 3
      }
    ]
  }
}
11. Переменные окружения (.env)
env
DEBUG=True
SECRET_KEY=your-secret-key-here

DB_NAME=warehouse_audit
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432

REDIS_URL=redis://localhost:6379/0

CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

FRONTEND_URL=http://localhost:8000
12. Критерии приёмки (Definition of Done)
Заказчик может пройти 20 вопросов, прерываясь и возвращаясь (сессия сохраняется).

После завершения видит цветной результат с баллами по 4 критериям.

Скачивает PDF-отчёт (один клик).

Администратор может менять текст вопросов, варианты ответов и веса через Django Admin без правки кода.

API полностью задокументирован (Swagger UI по /api/docs/).

Расчёт результатов повторяем (при одинаковых ответах → одинаковый балл).

Все миграции idempotent.

Celery-задачи не блокируют ответ API.

13. Дальнейшее развитие (v2.0 — режим консультанта)
Модель ProAuditAnswer с полями: comment, photo, video_url, voice_note.

Эндпоинт для пакетной загрузки фото (multipart/form-data).

Экспорт в Excel (все сессии + ответы).

Сравнение с бенчмарками (по отраслям, типу склада).

Возможность отправить отчёт клиенту на email (Celery + Django Email).