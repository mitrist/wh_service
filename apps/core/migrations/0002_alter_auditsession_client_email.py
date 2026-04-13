from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="auditsession",
            name="client_email",
            field=models.EmailField(blank=True, default="", max_length=254),
        ),
    ]
