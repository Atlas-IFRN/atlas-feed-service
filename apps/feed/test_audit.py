import uuid
from types import SimpleNamespace

from django.test import TestCase
from rest_framework.test import APIClient

from .audit import clear_current_actor_id, set_current_actor_id
from .models import AuditLog, Post


class FeedAuditSignalsTests(TestCase):
    def setUp(self):
        self.user_id = uuid.uuid4()
        set_current_actor_id(self.user_id)

    def tearDown(self):
        clear_current_actor_id()

    def test_post_changes_are_audited(self):
        post = Post.objects.create(author_id=self.user_id, content='Original')
        post.content = 'Atualizado'
        post.save()
        post_id = post.id
        post.delete()

        logs = AuditLog.objects.filter(table_name='post', record_id=post_id)
        self.assertEqual(
            set(logs.values_list('action', flat=True)),
            {'CREATE', 'UPDATE', 'DELETE'},
        )
        self.assertFalse(logs.exclude(user_id=self.user_id).exists())


class AuditLogAccessTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_only_teacher_can_list_audit_logs(self):
        student = SimpleNamespace(id=uuid.uuid4(), is_authenticated=True, role='STUDENT')
        teacher = SimpleNamespace(id=uuid.uuid4(), is_authenticated=True, role='TEACHER')

        self.client.force_authenticate(student)
        self.assertEqual(self.client.get('/api/feed/audit-logs/').status_code, 403)

        self.client.force_authenticate(teacher)
        self.assertEqual(self.client.get('/api/feed/audit-logs/').status_code, 200)
