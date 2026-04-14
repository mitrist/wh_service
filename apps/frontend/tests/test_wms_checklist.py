from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.core.models import NotificationLog, WmsChecklistAnswer, WmsChecklistSession
from apps.frontend.wms_checklist_data import count_ready_answers, resolve_wms_band
from apps.reporting.pdf_generator import build_wms_checklist_pdf_bytes


class ResolveWmsBandTests(TestCase):
    def test_boundaries(self):
        self.assertEqual(resolve_wms_band(0)["code"], "red")
        self.assertEqual(resolve_wms_band(3)["code"], "red")
        self.assertEqual(resolve_wms_band(4)["code"], "yellow")
        self.assertEqual(resolve_wms_band(6)["code"], "yellow")
        self.assertEqual(resolve_wms_band(7)["code"], "green")
        self.assertEqual(resolve_wms_band(8)["code"], "green")
        self.assertEqual(resolve_wms_band(9)["code"], "optimal")
        self.assertEqual(resolve_wms_band(10)["code"], "optimal")


class CountReadyTests(TestCase):
    def test_count(self):
        m = {i: None for i in range(1, 11)}
        self.assertEqual(count_ready_answers(m), 0)
        m[1] = "ready"
        m[2] = "ready"
        m[3] = "not_ready"
        self.assertEqual(count_ready_answers(m), 2)


class WmsChecklistModelTests(TestCase):
    def test_unique_session_item(self):
        s = WmsChecklistSession.objects.create()
        WmsChecklistAnswer.objects.create(session=s, item_number=1, status="ready")
        with self.assertRaises(IntegrityError):
            WmsChecklistAnswer.objects.create(session=s, item_number=1, status="not_ready")


class WmsChecklistViewTests(TestCase):
    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        CELERY_TASK_ALWAYS_EAGER=True,
        NOTIFICATIONS_ENABLED=True,
        FORM_NOTIFY_WMS_CHECKLIST_EMAILS=["ops@example.com"],
    )
    def test_notification_sent_when_all_items_answered(self):
        s = WmsChecklistSession.objects.create()
        for n in range(1, 11):
            WmsChecklistAnswer.objects.create(session=s, item_number=n, status=None)
        url = reverse("frontend_wms_checklist_answer", kwargs={"session_id": s.id})
        for n in range(1, 11):
            body = f'{{"item_number": {n}, "status": "ready"}}'
            r = self.client.post(url, data=body, content_type="application/json")
            self.assertEqual(r.status_code, 200)
        self.assertTrue(
            NotificationLog.objects.filter(
                event_type="wms_checklist_completed",
                entity_id=str(s.id),
            ).exists(),
        )

    def test_begin_redirect_and_seeds_answers(self):
        url = reverse("frontend_wms_checklist_begin")
        r = self.client.post(url)
        self.assertEqual(r.status_code, 302)
        sid = WmsChecklistSession.objects.first().id
        self.assertEqual(WmsChecklistAnswer.objects.filter(session_id=sid).count(), 10)

    def test_answer_updates(self):
        s = WmsChecklistSession.objects.create()
        for n in range(1, 11):
            WmsChecklistAnswer.objects.create(session=s, item_number=n, status=None)
        url = reverse("frontend_wms_checklist_answer", kwargs={"session_id": s.id})
        body = '{"item_number": 3, "status": "ready"}'
        r = self.client.post(url, data=body, content_type="application/json")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["ok"])
        self.assertEqual(WmsChecklistAnswer.objects.get(session=s, item_number=3).status, "ready")

    def test_answer_bad_status(self):
        s = WmsChecklistSession.objects.create()
        WmsChecklistAnswer.objects.create(session=s, item_number=1, status=None)
        url = reverse("frontend_wms_checklist_answer", kwargs={"session_id": s.id})
        r = self.client.post(
            url,
            data='{"item_number": 1, "status": "maybe"}',
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)

    def test_answer_bad_item(self):
        s = WmsChecklistSession.objects.create()
        WmsChecklistAnswer.objects.create(session=s, item_number=1, status=None)
        url = reverse("frontend_wms_checklist_answer", kwargs={"session_id": s.id})
        r = self.client.post(
            url,
            data='{"item_number": 99, "status": "ready"}',
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)


class WmsPdfTests(TestCase):
    def test_template_pdf(self):
        b = build_wms_checklist_pdf_bytes(session_id=None, status_by_item={})
        self.assertTrue(b.startswith(b"%PDF"))
        self.assertGreater(len(b), 2000)

    def test_session_pdf(self):
        st = {i: "ready" if i <= 7 else "not_ready" for i in range(1, 11)}
        b = build_wms_checklist_pdf_bytes(session_id="test-uuid", status_by_item=st)
        self.assertTrue(b.startswith(b"%PDF"))
