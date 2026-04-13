from uuid import UUID

from django.http import FileResponse, Http404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.serializers import (
    AnswerPatchSerializer,
    AuditSessionClientUpdateSerializer,
    AuditSessionCreateSerializer,
    AuditSessionDetailSerializer,
    QuestionSelfSerializer,
)
from apps.api.services import AnswerPatchInput, complete_session, patch_session_answer
from apps.core.models import AuditReport, AuditSession, Question
from apps.reporting.tasks import generate_pdf_report


class SelfQuestionsView(APIView):
    @extend_schema(responses=QuestionSelfSerializer(many=True))
    def get(self, request):
        qs = (
            Question.objects.filter(is_self_audit=True, is_active=True, number__lte=21)
            .prefetch_related("options")
            .order_by("order")
        )
        return Response(QuestionSelfSerializer(qs, many=True).data)


class SessionListCreateView(APIView):
    @extend_schema(request=AuditSessionCreateSerializer, responses=AuditSessionCreateSerializer)
    def post(self, request):
        ser = AuditSessionCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        obj = ser.save()
        return Response(AuditSessionCreateSerializer(obj).data, status=status.HTTP_201_CREATED)


class SessionDetailView(APIView):
    @extend_schema(responses=AuditSessionDetailSerializer)
    def get(self, request, pk):
        session = self._get_session(pk)
        return Response(AuditSessionDetailSerializer(session).data)

    @extend_schema(
        request=AuditSessionClientUpdateSerializer,
        responses=AuditSessionDetailSerializer,
    )
    def patch(self, request, pk):
        session = self._get_session(pk)
        if session.status != "draft":
            return Response(
                {"detail": "Редактирование доступно только для черновика."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ser = AuditSessionClientUpdateSerializer(
            session,
            data=request.data,
            partial=True,
        )
        ser.is_valid(raise_exception=True)
        ser.save()
        fresh = (
            AuditSession.objects.prefetch_related(
                "answers__question",
                "answers__selected_option",
            ).get(pk=session.pk)
        )
        return Response(AuditSessionDetailSerializer(fresh).data)

    def _get_session(self, pk) -> AuditSession:
        try:
            UUID(str(pk))
        except ValueError as exc:
            raise Http404 from exc
        try:
            return AuditSession.objects.prefetch_related(
                "answers__question",
                "answers__selected_option",
            ).get(pk=pk)
        except AuditSession.DoesNotExist as exc:
            raise Http404 from exc


class SessionAnswersView(SessionDetailView):
    @extend_schema(request=AnswerPatchSerializer, responses=AuditSessionDetailSerializer)
    def patch(self, request, pk):
        session = self._get_session(pk)
        ser = AnswerPatchSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        try:
            patch_session_answer(
                session,
                AnswerPatchInput(
                    question_code=data["question_code"],
                    option_id=(data.get("option_id") or None) or None,
                    open_answer_text=data.get("open_answer_text"),
                ),
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        session.refresh_from_db()
        fresh = (
            AuditSession.objects.prefetch_related(
                "answers__question",
                "answers__selected_option",
            ).get(pk=session.pk)
        )
        return Response(AuditSessionDetailSerializer(fresh).data)


class SessionCompleteView(SessionDetailView):
    @extend_schema(
        responses={
            200: {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "status": {"type": "string"},
                    "message": {"type": "string"},
                    "result": {"type": "object"},
                },
            }
        },
    )
    def post(self, request, pk):
        session = self._get_session(pk)
        try:
            result, _report = complete_session(session)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        generate_pdf_report.delay(str(session.id))
        return Response(
            {
                "session_id": str(session.id),
                "status": "processing",
                "message": "Расчёт выполнен, PDF генерируется. Проверьте через несколько секунд.",
                "result": result,
            },
        )


class SessionReportView(SessionDetailView):
    def get(self, request, pk):
        session = self._get_session(pk)
        if session.status != "completed":
            return Response(
                {"detail": "Отчёт доступен только для завершённой сессии."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            report = session.report
        except AuditReport.DoesNotExist:
            return Response(
                {"detail": "Отчёт ещё не создан."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if not report.pdf_file:
            return Response(
                {
                    "detail": "PDF ещё генерируется. Повторите запрос позже.",
                    "status": "processing",
                },
                status=status.HTTP_202_ACCEPTED,
            )
        return FileResponse(
            report.pdf_file.open("rb"),
            as_attachment=True,
            filename=f"audit_report_{session.id}.pdf",
        )
