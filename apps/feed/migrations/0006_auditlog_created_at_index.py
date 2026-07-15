from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('feed', '0005_auditlog'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(
                fields=['-created_at'],
                name='feed_audit_created_idx',
            ),
        ),
    ]
