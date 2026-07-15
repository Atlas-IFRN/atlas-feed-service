import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('feed', '0004_banner'),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('table_name', models.CharField(choices=[('post', 'Post'), ('banner', 'Banner'), ('comment', 'Comment'), ('post_like', 'Post Like'), ('comment_like', 'Comment Like')], max_length=100)),
                ('action', models.CharField(choices=[('CREATE', 'Create'), ('UPDATE', 'Update'), ('DELETE', 'Delete')], max_length=10)),
                ('record_id', models.UUIDField(help_text='PK do registro afetado')),
                ('user_id', models.UUIDField(blank=True, db_index=True, help_text='UUID do usuário responsável pela operação', null=True)),
                ('payload', models.JSONField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Audit Log',
                'verbose_name_plural': 'Audit Logs',
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['user_id', '-created_at'], name='feed_audit_user_time_idx')],
            },
        ),
    ]
