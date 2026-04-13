from django.urls import path

from apps.frontend import views

urlpatterns = [
    path("", views.home, name="frontend_home"),
    path(
        "full-audit/request/",
        views.full_audit_lead_submit,
        name="frontend_full_audit_lead_submit",
    ),
    path("audit/begin/", views.audit_begin, name="frontend_audit_begin"),
    path("audit/<uuid:session_id>/", views.self_audit_session, name="frontend_self_audit_session"),
    path(
        "audit/<uuid:session_id>/contact/",
        views.self_audit_contact,
        name="frontend_self_audit_contact",
    ),
    path(
        "audit/<uuid:session_id>/result/",
        views.self_audit_result,
        name="frontend_self_audit_result",
    ),
]
