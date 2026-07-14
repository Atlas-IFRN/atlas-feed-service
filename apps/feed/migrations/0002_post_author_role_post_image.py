import apps.feed.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('feed', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='author_role',
            field=models.CharField(
                choices=[
                    ('STUDENT', 'Estudante'),
                    ('TEACHER', 'Professor'),
                    ('SYSTEM', 'Sistema'),
                ],
                db_index=True,
                default='STUDENT',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='post',
            name='image',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to=apps.feed.models.post_image_upload_to,
            ),
        ),
    ]
