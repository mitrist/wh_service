from django.urls import path

from apps.api import views

urlpatterns = [
    path("questions/self/", views.SelfQuestionsView.as_view(), name="api_questions_self"),
    path("sessions/", views.SessionListCreateView.as_view(), name="api_sessions"),
    path("sessions/<uuid:pk>/", views.SessionDetailView.as_view(), name="api_session_detail"),
    path(
        "sessions/<uuid:pk>/answers/",
        views.SessionAnswersView.as_view(),
        name="api_session_answers",
    ),
    path(
        "sessions/<uuid:pk>/complete/",
        views.SessionCompleteView.as_view(),
        name="api_session_complete",
    ),
    path(
        "sessions/<uuid:pk>/report/",
        views.SessionReportView.as_view(),
        name="api_session_report",
    ),
]
