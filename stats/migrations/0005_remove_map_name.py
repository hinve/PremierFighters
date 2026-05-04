from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("stats", "0004_playermatchstats_agent_name"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="playermatchstats",
            unique_together={('player', 'match')},
        ),
        migrations.RemoveField(
            model_name="playermatchstats",
            name="map_name",
        ),
    ]
