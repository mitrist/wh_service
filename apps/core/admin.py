from django.contrib import admin
from django.utils.html import format_html

from apps.core.models import (
    AnswerOption,
    AuditReport,
    AuditSession,
    FullAuditLead,
    Question,
    UserAnswer,
    WmsChecklistAnswer,
    WmsChecklistSession,
)
from apps.reporting.tasks import generate_pdf_report


class AnswerOptionInline(admin.TabularInline):
    model = AnswerOption
    extra = 0
    fields = ("code", "text", "score_percent", "after_answer_comment", "order")


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("code", "number", "category", "weight", "is_active", "is_self_audit")
    list_filter = ("category", "weight", "is_active", "is_self_audit")
    search_fields = ("code", "text")
    inlines = [AnswerOptionInline]


class UserAnswerInline(admin.TabularInline):
    model = UserAnswer
    extra = 0
    readonly_fields = ("question", "selected_option", "open_answer_text")
    can_delete = False


@admin.register(AuditSession)
class AuditSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "mode", "status", "client_email", "started_at", "completed_at")
    list_filter = ("mode", "status")
    search_fields = ("client_email", "client_company", "client_name")
    readonly_fields = ("id", "started_at", "last_modified", "completed_at")
    inlines = [UserAnswerInline]
    actions = ["action_regenerate_pdf"]

    @admin.action(description="Пересобрать PDF (Celery)")
    def action_regenerate_pdf(self, request, queryset):
        for s in queryset.filter(status="completed"):
            generate_pdf_report.delay(str(s.id))


class WmsChecklistAnswerInline(admin.TabularInline):
    model = WmsChecklistAnswer
    extra = 0
    fields = ("item_number", "status")
    ordering = ("item_number",)


@admin.register(WmsChecklistSession)
class WmsChecklistSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at", "updated_at", "answers_filled")
    list_filter = ("created_at",)
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = [WmsChecklistAnswerInline]
    ordering = ("-created_at",)

    @admin.display(description="Заполнено ответов")
    def answers_filled(self, obj: WmsChecklistSession) -> int:
        return obj.answers.exclude(status__isnull=True).exclude(status="").count()


@admin.register(FullAuditLead)
class FullAuditLeadAdmin(admin.ModelAdmin):
    list_display = ("created_at", "name", "contact", "preferred_method", "email_sent")
    list_filter = ("preferred_method", "email_sent", "created_at")
    search_fields = ("name", "contact")
    readonly_fields = ("created_at", "email_sent", "email_error")
    ordering = ("-created_at",)


@admin.register(AuditReport)
class AuditReportAdmin(admin.ModelAdmin):
    list_display = ("session", "generated_at", "pdf_link")
    readonly_fields = ("session", "generated_at", "summary")

    @admin.display(description="PDF")
    def pdf_link(self, obj):
        if obj.pdf_file:
            return format_html('<a href="{}">скачать</a>', obj.pdf_file.url)
        return "—"
