from rest_framework import serializers

from apps.core.models import AnswerOption, AuditSession, Question, UserAnswer


class AnswerOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnswerOption
        fields = ("id", "code", "text", "score_percent", "after_answer_comment", "order")


class QuestionSelfSerializer(serializers.ModelSerializer):
    options = AnswerOptionSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = (
            "id",
            "code",
            "number",
            "text",
            "category",
            "weight",
            "order",
            "hint",
            "check_note",
            "options",
        )


class AuditSessionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditSession
        fields = (
            "id",
            "mode",
            "status",
            "client_name",
            "client_company",
            "client_email",
            "started_at",
            "total_score",
            "total_grade",
        )
        read_only_fields = ("id", "status", "started_at", "total_score", "total_grade")
        extra_kwargs = {
            "client_email": {"required": False, "allow_blank": True},
            "client_name": {"required": False, "allow_blank": True},
            "client_company": {"required": False, "allow_blank": True},
        }

    def create(self, validated_data):
        validated_data.setdefault("mode", "self")
        validated_data.setdefault("status", "draft")
        validated_data.setdefault("client_email", "")
        return super().create(validated_data)


class AuditSessionClientUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditSession
        fields = ("client_name", "client_company", "client_email")
        extra_kwargs = {
            "client_email": {"required": False, "allow_blank": True},
            "client_name": {"required": False, "allow_blank": True},
            "client_company": {"required": False, "allow_blank": True},
        }


class UserAnswerSerializer(serializers.ModelSerializer):
    question_code = serializers.CharField(source="question.code", read_only=True)
    option_id = serializers.CharField(source="selected_option.code", read_only=True)

    class Meta:
        model = UserAnswer
        fields = (
            "question_code",
            "option_id",
            "open_answer_text",
        )


class AuditSessionDetailSerializer(serializers.ModelSerializer):
    answers = UserAnswerSerializer(many=True, read_only=True)

    class Meta:
        model = AuditSession
        fields = (
            "id",
            "mode",
            "status",
            "client_name",
            "client_company",
            "client_email",
            "started_at",
            "completed_at",
            "last_modified",
            "total_score",
            "total_grade",
            "answers",
        )


class AnswerPatchSerializer(serializers.Serializer):
    question_code = serializers.CharField(max_length=32)
    option_id = serializers.CharField(max_length=64, required=False, allow_blank=True)
    open_answer_text = serializers.CharField(required=False, allow_blank=True)
