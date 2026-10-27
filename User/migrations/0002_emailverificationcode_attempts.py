from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('User', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='emailverificationcode',
            name='attempts',
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]
