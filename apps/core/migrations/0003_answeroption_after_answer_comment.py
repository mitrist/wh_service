from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_alter_auditsession_client_email"),
    ]

    operations = [
        migrations.AddField(
            model_name="answeroption",
            name="after_answer_comment",
            field=models.TextField(blank=True, default=""),
        ),
    ]
