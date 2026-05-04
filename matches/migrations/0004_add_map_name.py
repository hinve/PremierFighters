from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("matches", "0003_alter_match_result"),
    ]

    operations = [
        migrations.AddField(
            model_name="match",
            name="map_name",
            field=models.CharField(max_length=100, blank=True, default=""),
        ),
    ]
