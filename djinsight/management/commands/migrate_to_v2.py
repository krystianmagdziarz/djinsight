from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction

from djinsight.models import (
    ContentTypeRegistry,
    PageViewEvent,
    PageViewStatistics,
    PageViewSummary,
)


class Command(BaseCommand):
    help = 'Migrate data from djinsight v0.1.x to v0.2.0'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run migration without saving changes',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Batch size for processing records',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        batch_size = options['batch_size']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be saved'))

        self.stdout.write('Starting migration from v0.1.x to v0.2.0...')

        try:
            migrated_logs = self._migrate_page_view_logs(dry_run, batch_size)
            migrated_summaries = self._migrate_summaries(dry_run, batch_size)
            migrated_stats = self._migrate_statistics(dry_run, batch_size)
            registered_types = self._register_content_types(dry_run)

            self.stdout.write(self.style.SUCCESS(f'\nMigration completed successfully!'))
            self.stdout.write(f'- Page View Events migrated: {migrated_logs}')
            self.stdout.write(f'- Summaries migrated: {migrated_summaries}')
            self.stdout.write(f'- Statistics migrated: {migrated_stats}')
            self.stdout.write(f'- Content Types registered: {registered_types}')

            if not dry_run:
                self.stdout.write(
                    self.style.WARNING('\nIMPORTANT: Old tables (PageViewLog with mixin fields) can now be safely removed.')
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Migration failed: {e}'))
            raise

    def _migrate_page_view_logs(self, dry_run, batch_size):
        try:
            from djinsight.models import PageViewLog as OldPageViewLog

            count = 0
            queryset = OldPageViewLog.objects.all().order_by('id')
            total = queryset.count()

            if total == 0:
                return 0

            self.stdout.write(f'\nMigrating {total} PageViewLog records...')

            for i in range(0, total, batch_size):
                batch = list(queryset[i:i + batch_size])
                new_events = []

                for log in batch:
                    try:
                        parts = log.content_type.split('.')
                        if len(parts) != 2:
                            continue

                        app_label, model = parts
                        content_type = ContentType.objects.get(app_label=app_label, model=model.lower())

                        new_events.append(PageViewEvent(
                            content_type=content_type,
                            object_id=log.page_id,
                            url=log.url,
                            session_key=log.session_key or '',
                            ip_address=log.ip_address,
                            user_agent=log.user_agent,
                            referrer=log.referrer,
                            timestamp=log.timestamp,
                            is_unique=log.is_unique,
                        ))
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'Skipping log {log.id}: {e}'))
                        continue

                if not dry_run and new_events:
                    PageViewEvent.objects.bulk_create(new_events, batch_size=500, ignore_conflicts=True)

                count += len(new_events)
                if i % (batch_size * 5) == 0:
                    self.stdout.write(f'Processed {count}/{total} logs...')

            return count
        except ImportError:
            self.stdout.write(self.style.WARNING('Old PageViewLog model not found, skipping...'))
            return 0

    def _migrate_summaries(self, dry_run, batch_size):
        try:
            from djinsight.models import PageViewSummary as OldPageViewSummary

            count = 0
            old_queryset = OldPageViewSummary.objects.all().order_by('id')
            total = old_queryset.count()

            if total == 0:
                return 0

            self.stdout.write(f'\nMigrating {total} PageViewSummary records...')

            for i in range(0, total, batch_size):
                batch = list(old_queryset[i:i + batch_size])
                new_summaries = []

                for summary in batch:
                    try:
                        parts = summary.content_type.split('.')
                        if len(parts) != 2:
                            continue

                        app_label, model = parts
                        content_type_obj = ContentType.objects.get(app_label=app_label, model=model.lower())

                        existing = PageViewSummary.objects.filter(
                            content_type=content_type_obj,
                            object_id=summary.page_id,
                            date=summary.date
                        ).exists()

                        if not existing:
                            new_summaries.append(PageViewSummary(
                                content_type=content_type_obj,
                                object_id=summary.page_id,
                                date=summary.date,
                                total_views=summary.total_views,
                                unique_views=summary.unique_views,
                            ))
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'Skipping summary {summary.id}: {e}'))
                        continue

                if not dry_run and new_summaries:
                    PageViewSummary.objects.bulk_create(new_summaries, batch_size=500, ignore_conflicts=True)

                count += len(new_summaries)
                if i % (batch_size * 5) == 0:
                    self.stdout.write(f'Processed {count}/{total} summaries...')

            return count
        except ImportError:
            return 0

    def _migrate_statistics(self, dry_run, batch_size):
        from django.apps import apps

        count = 0
        self.stdout.write('\nMigrating statistics from models with PageViewStatisticsMixin...')

        for model in apps.get_models():
            if not all(hasattr(model, f) for f in ['total_views', 'unique_views', 'first_viewed_at', 'last_viewed_at']):
                continue

            content_type = ContentType.objects.get_for_model(model)
            queryset = model.objects.all()
            total = queryset.count()

            if total == 0:
                continue

            self.stdout.write(f'Found {total} objects in {content_type}...')

            for i in range(0, total, batch_size):
                batch = list(queryset[i:i + batch_size])
                new_stats = []

                for obj in batch:
                    if obj.total_views == 0 and obj.unique_views == 0:
                        continue

                    existing = PageViewStatistics.objects.filter(
                        content_type=content_type,
                        object_id=obj.pk
                    ).exists()

                    if not existing:
                        new_stats.append(PageViewStatistics(
                            content_type=content_type,
                            object_id=obj.pk,
                            total_views=obj.total_views,
                            unique_views=obj.unique_views,
                            first_viewed_at=obj.first_viewed_at,
                            last_viewed_at=obj.last_viewed_at,
                        ))

                if not dry_run and new_stats:
                    PageViewStatistics.objects.bulk_create(new_stats, batch_size=500, ignore_conflicts=True)

                count += len(new_stats)

            self.stdout.write(f'Migrated {count} statistics from {content_type}')

        return count

    def _register_content_types(self, dry_run):
        from django.apps import apps

        count = 0
        self.stdout.write('\nRegistering content types...')

        tracked_models = set()

        for model in apps.get_models():
            if all(hasattr(model, f) for f in ['total_views', 'unique_views', 'first_viewed_at', 'last_viewed_at']):
                tracked_models.add(model)

        for event in PageViewEvent.objects.values('content_type').distinct():
            try:
                content_type = ContentType.objects.get(id=event['content_type'])
                model_class = content_type.model_class()
                if model_class:
                    tracked_models.add(model_class)
            except:
                pass

        for model in tracked_models:
            content_type = ContentType.objects.get_for_model(model)

            if not dry_run:
                ContentTypeRegistry.objects.get_or_create(
                    content_type=content_type,
                    defaults={'enabled': True}
                )
            count += 1
            self.stdout.write(f'Registered: {content_type}')

        return count
