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
