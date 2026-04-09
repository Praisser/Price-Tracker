from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_priceresult_image_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='priceresult',
            name='match_confidence',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='priceresult',
            name='title',
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.CreateModel(
            name='SourceStatus',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('website', models.CharField(max_length=100)),
                ('state', models.CharField(choices=[('matched', 'Matched'), ('ambiguous', 'Ambiguous'), ('blocked', 'Blocked'), ('not_found', 'Not Found'), ('unavailable', 'Unavailable'), ('error', 'Error')], max_length=20)),
                ('checked_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('diagnostic_message', models.TextField(blank=True)),
                ('matched_title', models.CharField(blank=True, max_length=500)),
                ('match_confidence', models.FloatField(blank=True, null=True)),
                ('http_status', models.PositiveIntegerField(blank=True, null=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='source_statuses', to='core.product')),
            ],
            options={
                'ordering': ['product', 'website'],
                'verbose_name_plural': 'Source statuses',
                'unique_together': {('product', 'website')},
            },
        ),
    ]
