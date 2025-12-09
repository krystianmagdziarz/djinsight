from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('djinsight', '0003_alter_pageviewlog_session_key'),
    ]

    operations = [
        migrations.CreateModel(
            name='ContentTypeRegistry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('enabled', models.BooleanField(default=True, verbose_name='Enabled')),
                ('track_anonymous', models.BooleanField(default=True, verbose_name='Track Anonymous')),
                ('track_authenticated', models.BooleanField(default=True, verbose_name='Track Authenticated')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated At')),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype', unique=True, verbose_name='Content Type')),
            ],
            options={
                'verbose_name': 'Content Type Registry',
                'verbose_name_plural': 'Content Type Registries',
            },
        ),
        migrations.CreateModel(
            name='PageViewStatistics',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('object_id', models.PositiveIntegerField(db_index=True)),
                ('total_views', models.PositiveIntegerField(default=0, verbose_name='Total Views')),
                ('unique_views', models.PositiveIntegerField(default=0, verbose_name='Unique Views')),
                ('first_viewed_at', models.DateTimeField(blank=True, null=True, verbose_name='First Viewed At')),
                ('last_viewed_at', models.DateTimeField(blank=True, null=True, verbose_name='Last Viewed At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated At')),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype')),
            ],
            options={
                'verbose_name': 'Page View Statistics',
                'verbose_name_plural': 'Page View Statistics',
                'ordering': ['-total_views'],
            },
        ),
        migrations.CreateModel(
            name='PageViewEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('object_id', models.PositiveIntegerField()),
                ('url', models.CharField(max_length=500, verbose_name='URL')),
                ('session_key', models.CharField(db_index=True, max_length=255, verbose_name='Session Key')),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True, verbose_name='IP Address')),
                ('user_agent', models.TextField(blank=True, null=True, verbose_name='User Agent')),
                ('referrer', models.URLField(blank=True, max_length=500, null=True, verbose_name='Referrer')),
                ('timestamp', models.DateTimeField(db_index=True, default=django.utils.timezone.now, verbose_name='Timestamp')),
                ('is_unique', models.BooleanField(default=False, verbose_name='Is Unique')),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype')),
            ],
            options={
                'verbose_name': 'Page View Event',
                'verbose_name_plural': 'Page View Events',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.AlterField(
            model_name='pageviewsummary',
            name='content_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype'),
        ),
        migrations.AlterField(
            model_name='pageviewsummary',
            name='page_id',
            field=models.PositiveIntegerField(db_index=True, verbose_name='Object ID'),
        ),
        migrations.AddIndex(
            model_name='contenttyperegistry',
            index=models.Index(fields=['content_type', 'enabled'], name='djinsight_c_content_idx'),
        ),
        migrations.AddIndex(
            model_name='pageviewstatistics',
            index=models.Index(fields=['content_type', 'object_id'], name='djinsight_p_content_obj_idx'),
        ),
        migrations.AddIndex(
            model_name='pageviewstatistics',
            index=models.Index(fields=['content_type', 'total_views'], name='djinsight_p_content_tot_idx'),
        ),
        migrations.AddIndex(
            model_name='pageviewstatistics',
            index=models.Index(fields=['content_type', 'unique_views'], name='djinsight_p_content_uni_idx'),
        ),
        migrations.AddIndex(
            model_name='pageviewstatistics',
            index=models.Index(fields=['last_viewed_at'], name='djinsight_p_last_vi_idx'),
        ),
        migrations.AddIndex(
            model_name='pageviewstatistics',
            index=models.Index(fields=['updated_at'], name='djinsight_p_updated_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='pageviewstatistics',
            unique_together={('content_type', 'object_id')},
        ),
        migrations.AddIndex(
            model_name='pageviewevent',
            index=models.Index(fields=['content_type', 'object_id', 'timestamp'], name='djinsight_p_content_obj_tim_idx'),
        ),
        migrations.AddIndex(
            model_name='pageviewevent',
            index=models.Index(fields=['session_key', 'content_type', 'object_id'], name='djinsight_p_session_con_idx'),
        ),
        migrations.AddIndex(
            model_name='pageviewevent',
            index=models.Index(fields=['timestamp'], name='djinsight_p_timesta_idx'),
        ),
        migrations.AddIndex(
            model_name='pageviewevent',
            index=models.Index(fields=['content_type', 'timestamp'], name='djinsight_p_content_tim_idx'),
        ),
        migrations.RenameField(
            model_name='pageviewsummary',
            old_name='page_id',
            new_name='object_id',
        ),
        migrations.AlterField(
            model_name='pageviewsummary',
            name='content_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype'),
        ),
        migrations.AddIndex(
            model_name='pageviewsummary',
            index=models.Index(fields=['content_type', 'object_id', 'date'], name='djinsight_p_content_obj_dat_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='pageviewsummary',
            unique_together={('content_type', 'object_id', 'date')},
        ),
    ]
