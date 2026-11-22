from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0002_document_signatories")]

    operations = [
        migrations.AddField(
            model_name="user",
            name="position",
            field=models.CharField(
                "посада", max_length=150, blank=True, default="", db_default=""
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="phone",
            field=models.CharField(
                "контактний телефон",
                max_length=50,
                blank=True,
                default="",
                db_default="",
            ),
        ),
    ]
