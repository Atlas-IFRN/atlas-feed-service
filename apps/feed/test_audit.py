import uuid

from django.test import TestCase

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
