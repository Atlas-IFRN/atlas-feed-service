from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('feed', '0002_post_author_role_post_image'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='is_fixed',
            field=models.BooleanField(default=False, db_index=True),
        ),
    ]
