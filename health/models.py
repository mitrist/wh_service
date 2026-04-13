from __future__ import annotations

from django.db import models


class HealthSelfAuditResult(models.Model):
    """
    Результат self-audit клиента (самодиагностика склада).

    Храним:
    - ответы пользователя (q1..q20_text),
    - вычисленный агрегат (overall + 4 критерия + top-3 разрывы),
    - дублируем итоговые проценты отдельными полями для удобных запросов.
    """

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    # Сырые ответы и рассчитанный агрегат (контекст для шаблонов).
    answers_json = models.JSONField(default=dict)
    result_json = models.JSONField(default=dict)

    # Итоговые поля (для быстрых выборок/фильтров).
    overall_index = models.IntegerField()
    overall_zone = models.CharField(max_length=16)

    accuracy_percent = models.IntegerField()
    speed_percent = models.IntegerField()
    capacity_percent = models.IntegerField()
    manageability_percent = models.IntegerField()

    class Meta:
        verbose_name = "Результат self-audit"
        verbose_name_plural = "Результаты self-audit"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Self-audit #{self.pk}: {self.overall_index}%"
