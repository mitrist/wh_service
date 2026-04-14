from django.urls import path

from apps.frontend import views
from apps.frontend import views_wms

urlpatterns = [
    path("", views.home, name="frontend_home"),
    path("about/", views.about_company, name="frontend_about_company"),
    path(
        "solutions/1s-wms-logistika-upravlenie-skladom/",
        views.solution_1c_wms,
        name="frontend_solution_1c_wms",
    ),
    path("services/<slug:slug>/", views.service_detail, name="frontend_service_detail"),
    path("solutions/", views.solutions, name="frontend_solutions"),
    path("solutions/<slug:slug>/", views.solution_detail, name="frontend_solution_detail"),
    path("self-audit/", views.self_audit_landing, name="frontend_self_audit_landing"),
    path("wms-checklist/", views_wms.wms_checklist_landing, name="frontend_wms_checklist_landing"),
    path("wms-checklist/begin/", views_wms.wms_checklist_begin, name="frontend_wms_checklist_begin"),
    path(
        "wms-checklist/pdf/template/",
        views_wms.wms_checklist_pdf_template,
        name="frontend_wms_checklist_pdf_template",
    ),
    path(
        "wms-checklist/<uuid:session_id>/answer/",
        views_wms.wms_checklist_answer,
        name="frontend_wms_checklist_answer",
    ),
    path(
        "wms-checklist/<uuid:session_id>/pdf/",
        views_wms.wms_checklist_pdf_session,
        name="frontend_wms_checklist_pdf_session",
    ),
    path(
        "wms-checklist/<uuid:session_id>/",
        views_wms.wms_checklist_session,
        name="frontend_wms_checklist_session",
    ),
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
