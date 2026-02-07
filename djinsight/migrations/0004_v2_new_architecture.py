from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


def convert_content_type_strings_to_ids(apps, schema_editor):
    """Convert string content_type values (e.g. 'puput.entrypage') to integer ContentType IDs."""
    PageViewSummary = apps.get_model('djinsight', 'PageViewSummary')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    distinct_types = (
        PageViewSummary.objects.values_list('content_type', flat=True).distinct()
    )

    for ct_string in distinct_types:
        if not ct_string or not isinstance(ct_string, str):
            continue

        parts = ct_string.split('.')
        if len(parts) != 2:
            continue

        app_label, model = parts
        try:
            ct = ContentType.objects.get(
                app_label=app_label, model=model.lower()
            )
            PageViewSummary.objects.filter(content_type=ct_string).update(
                content_type=str(ct.id)
            )
        except ContentType.DoesNotExist:
            pass


def migrate_mixin_statistics(apps, schema_editor):
    """Migrate total_views/unique_views from models with PageViewStatisticsMixin fields
    into the new PageViewStatistics table.

    Uses raw SQL to discover tables with mixin columns because at migration time
    the Python model class may have already removed the mixin (code runs ahead of migrations).
    """
    connection = schema_editor.connection
    ContentType = apps.get_model('contenttypes', 'ContentType')

    with connection.cursor() as cursor:
        # Find all tables that have the mixin columns
        cursor.execute("""
            SELECT table_schema, table_name
            FROM information_schema.columns
            WHERE column_name = 'total_views'
            AND table_name NOT LIKE 'djinsight_%%'
            GROUP BY table_schema, table_name
            HAVING COUNT(*) FILTER (WHERE column_name IN ('total_views', 'unique_views', 'first_viewed_at', 'last_viewed_at')) >= 1
        """)
        tables = cursor.fetchall()

        for table_schema, table_name in tables:
            # Resolve app_label and model from the table name via django_content_type
            # Table names follow pattern: app_model (e.g., puput_entrypage)
            parts = table_name.split('_', 1)
            if len(parts) != 2:
                continue

            app_label, model_name = parts

            try:
                ct = ContentType.objects.get(
                    app_label=app_label, model=model_name
                )
            except ContentType.DoesNotExist:
                continue

            # Check which columns actually exist
            cursor.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                AND column_name IN ('total_views', 'unique_views', 'first_viewed_at', 'last_viewed_at')
            """, [table_schema, table_name])
            existing_cols = {row[0] for row in cursor.fetchall()}

            if 'total_views' not in existing_cols:
                continue

            # Find the primary key column
            cursor.execute("""
                SELECT column_name FROM information_schema.key_column_usage
                WHERE table_schema = %s AND table_name = %s
                AND constraint_name LIKE '%%pkey'
                LIMIT 1
            """, [table_schema, table_name])
            pk_row = cursor.fetchone()
            pk_col = pk_row[0] if pk_row else 'id'

            # Build and run the INSERT from the mixin table into PageViewStatistics
            schema_prefix = f'"{table_schema}".' if table_schema and table_schema != 'public' else ''

            first_viewed = 'first_viewed_at' if 'first_viewed_at' in existing_cols else 'NULL'
            last_viewed = 'last_viewed_at' if 'last_viewed_at' in existing_cols else 'NULL'
            unique_views = 'COALESCE(unique_views, 0)' if 'unique_views' in existing_cols else '0'

            cursor.execute(f"""
                INSERT INTO {schema_prefix}"djinsight_pageviewstatistics"
                    (content_type_id, object_id, total_views, unique_views, first_viewed_at, last_viewed_at, updated_at)
                SELECT
                    %s, "{pk_col}", COALESCE(total_views, 0), {unique_views}, {first_viewed}, {last_viewed}, NOW()
                FROM {schema_prefix}"{table_name}"
                WHERE total_views > 0 OR unique_views > 0
            """, [ct.id])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('djinsight', '0003_alter_pageviewlog_session_key'),
    ]

    operations = [
        # Create new models first
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
        # DATA MIGRATION: Convert string content_type to integer IDs BEFORE AlterField
        migrations.RunPython(
            convert_content_type_strings_to_ids,
            noop,
        ),
        # DATA MIGRATION: Migrate mixin statistics to PageViewStatistics table
        migrations.RunPython(
            migrate_mixin_statistics,
            noop,
        ),
        # Now safe to alter content_type from CharField to ForeignKey
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
        # Indexes for new models
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
