from __future__ import annotations

import uuid

from django.db import models


class AuditSession(models.Model):
    MODE_CHOICES = (
        ("self", "Self-audit (заказчик)"),
        ("pro", "Pro-аудит (консультант)"),
    )
    STATUS_CHOICES = (
        ("draft", "Черновик"),
        ("completed", "Завершён"),
        ("archived", "В архиве"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mode = models.CharField(max_length=10, choices=MODE_CHOICES, default="self")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft")

    client_name = models.CharField(max_length=200, blank=True)
    client_company = models.CharField(max_length=200, blank=True)
    client_email = models.EmailField(blank=True, default="")

    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_modified = models.DateTimeField(auto_now=True)

    total_score = models.FloatField(null=True, blank=True)
    total_grade = models.CharField(max_length=10, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "client_email"]),
            models.Index(fields=["mode", "completed_at"]),
        ]

    def __str__(self) -> str:
        return f"AuditSession {self.id} ({self.status})"


class Question(models.Model):
    CATEGORY_CHOICES = (
        ("accuracy", "Точность"),
        ("speed", "Скорость"),
        ("capacity", "Ёмкость"),
        ("manageability", "Управляемость"),
    )

    code = models.CharField(max_length=10, unique=True)
    number = models.PositiveSmallIntegerField(unique=True)
    text = models.TextField()
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        blank=True,
    )
    weight = models.PositiveSmallIntegerField(default=1)
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_self_audit = models.BooleanField(default=True)

    hint = models.TextField(blank=True)
    check_note = models.TextField(blank=True)
    impact_text = models.TextField(blank=True)
    self_recommendation = models.TextField(blank=True)
    pro_recommendation = models.TextField(blank=True)

    class Meta:
        ordering = ["order"]

    def __str__(self) -> str:
        return f"{self.code}"


class AnswerOption(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="options",
    )
    code = models.CharField(max_length=32)
    text = models.CharField(max_length=500)
    score_percent = models.IntegerField()
    after_answer_comment = models.TextField(blank=True, default="")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["question", "code"],
                name="unique_answer_option_code_per_question",
            ),
            models.UniqueConstraint(
                fields=["question", "order"],
                name="unique_answer_option_order_per_question",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code}"


class UserAnswer(models.Model):
    session = models.ForeignKey(
        AuditSession,
        on_delete=models.CASCADE,
        related_name="answers",
    )
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.ForeignKey(
        AnswerOption,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    open_answer_text = models.TextField(blank=True)
    comment = models.TextField(blank=True)
    photo = models.ImageField(
        upload_to="audit_photos/%Y/%m/%d/",
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session", "question"],
                name="unique_user_answer_per_session_question",
            ),
        ]


def audit_report_upload_to(instance: "AuditReport", filename: str) -> str:
    return f"reports/session_{instance.session_id}/{filename}"


class AuditReport(models.Model):
    session = models.OneToOneField(
        AuditSession,
        on_delete=models.CASCADE,
        related_name="report",
    )
    pdf_file = models.FileField(
        upload_to=audit_report_upload_to,
        blank=True,
        null=True,
    )
    generated_at = models.DateTimeField(auto_now_add=True)
    summary = models.JSONField(default=dict)

    def __str__(self) -> str:
        return f"Report for {self.session_id}"


class FullAuditLead(models.Model):
    """Заявка из модального окна «Заказать полный аудит» на лендинге."""

    METHOD_EMAIL = "email"
    METHOD_PHONE = "phone"
    PREFERRED_METHOD_CHOICES = (
        (METHOD_EMAIL, "Email"),
        (METHOD_PHONE, "Телефон"),
    )

    name = models.CharField("Имя", max_length=200)
    contact = models.CharField("Email или телефон", max_length=500)
    preferred_method = models.CharField(
        "Предпочитаемый способ связи",
        max_length=16,
        choices=PREFERRED_METHOD_CHOICES,
    )
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    email_sent = models.BooleanField("Письмо отправлено", default=False)
    email_error = models.TextField("Ошибка отправки почты", blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Заявка на полный аудит"
        verbose_name_plural = "Заявки на полный аудит"

    def __str__(self) -> str:
        return f"{self.name} ({self.created_at:%Y-%m-%d %H:%M})"


class NotificationLog(models.Model):
    STATUS_PENDING = "pending"
    STATUS_SENT = "sent"
    STATUS_SKIPPED = "skipped"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = (
        (STATUS_PENDING, "В очереди"),
        (STATUS_SENT, "Отправлено"),
        (STATUS_SKIPPED, "Пропущено"),
        (STATUS_FAILED, "Ошибка"),
    )

    event_type = models.CharField(max_length=64)
    entity_id = models.CharField(max_length=64)
    recipient_group = models.CharField(max_length=64, default="internal")
    recipients = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)
    attempts = models.PositiveIntegerField(default=0)
    error = models.TextField(blank=True, default="")
    message_id = models.CharField(max_length=255, blank=True, default="")
    payload = models.JSONField(default=dict, blank=True)
    context = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["event_type", "entity_id", "recipient_group"],
                name="uniq_notification_event_entity_group",
            ),
        ]
        indexes = [
            models.Index(fields=["event_type", "entity_id"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.event_type}:{self.entity_id}:{self.recipient_group}"


class WmsChecklistSession(models.Model):
    """Интерактивный чек-лист готовности к WMS (отдельно от самоаудита)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Сессия WMS чек-листа"
        verbose_name_plural = "Сессии WMS чек-листа"

    def __str__(self) -> str:
        return f"WmsChecklist {self.id}"


class WmsChecklistAnswer(models.Model):
    STATUS_READY = "ready"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_NOT_READY = "not_ready"
    STATUS_CHOICES = (
        (STATUS_READY, "Готово"),
        (STATUS_IN_PROGRESS, "В процессе"),
        (STATUS_NOT_READY, "Не готово"),
    )

    session = models.ForeignKey(
        WmsChecklistSession,
        on_delete=models.CASCADE,
        related_name="answers",
    )
    item_number = models.PositiveSmallIntegerField()
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session", "item_number"],
                name="unique_wms_answer_per_session_item",
            ),
        ]
        ordering = ["item_number"]

    def __str__(self) -> str:
        return f"{self.session_id} #{self.item_number} {self.status or '—'}"
