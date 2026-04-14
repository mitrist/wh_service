from __future__ import annotations

from enum import StrEnum


class NotificationEvent(StrEnum):
    FULL_AUDIT_LEAD_CREATED = "full_audit_lead_created"
    SELF_AUDIT_CONTACT_CAPTURED = "self_audit_contact_captured"
    SELF_AUDIT_COMPLETED = "self_audit_completed"
    WMS_CHECKLIST_COMPLETED = "wms_checklist_completed"
