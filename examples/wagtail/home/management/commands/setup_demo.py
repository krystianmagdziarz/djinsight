"""Create demo pages for the Wagtail djinsight example."""
import random
from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.utils import timezone
from wagtail.models import Page, Site

from djinsight.models import PageViewEvent, PageViewStatistics
from home.models import BlogPage, HomePage


class Command(BaseCommand):
    help = "Set up demo pages and fake analytics data"

    def handle(self, *args, **options):
        # Replace default Wagtail welcome page with our HomePage
        root = Page.objects.get(depth=1)
        try:
            home = HomePage.objects.get(depth=2)
            self.stdout.write("HomePage already exists, skipping page creation")
        except HomePage.DoesNotExist:
            # Delete the default welcome page and fix treebeard state
            Page.objects.filter(depth=2).delete()
            root.numchild = 0
            root.save()

            home = HomePage(
                title="djinsight Demo",
                slug="home",
                body="<p>Welcome to the djinsight Wagtail integration demo. "
                "Browse the blog pages below to generate page views.</p>",
            )
            root.add_child(instance=home)

            # Update or create site to point to our homepage
            Site.objects.all().delete()
            Site.objects.create(
                hostname="localhost",
                root_page=home,
                is_default_site=True,
            )

            # Create blog pages
            posts = [
                ("Getting Started with djinsight", "How to add analytics tracking to your Django/Wagtail site."),
                ("Understanding Page View Statistics", "Learn about total views, unique views, and daily summaries."),
                ("MCP Integration Guide", "Connect your analytics to Claude via the Model Context Protocol."),
                ("Traffic Source Analysis", "Understand where your visitors come from."),
                ("Wagtail Admin Reports", "Using the built-in reports in the Wagtail admin."),
            ]
            for title, body in posts:
                page = BlogPage(title=title, body=f"<p>{body}</p>")
                home.add_child(instance=page)

            self.stdout.write(self.style.SUCCESS(f"Created HomePage + {len(posts)} BlogPages"))

        # Generate fake analytics data
        self._generate_fake_stats(home)
        self.stdout.write(self.style.SUCCESS("Demo setup complete!"))

    def _generate_fake_stats(self, home):
        now = timezone.now()
        all_pages = [home] + list(BlogPage.objects.all())

        for page in all_pages:
            ct = ContentType.objects.get_for_model(page)
            stats, created = PageViewStatistics.objects.get_or_create(
                content_type=ct,
                object_id=page.pk,
                defaults={
                    "total_views": 0,
                    "unique_views": 0,
                    "first_viewed_at": now - timedelta(days=7),
                    "last_viewed_at": now,
                },
            )
            if not created:
                self.stdout.write(f"  Stats already exist for '{page.title}', skipping events")
                continue

            total = random.randint(20, 200)
            unique = random.randint(10, total)
            stats.total_views = total
            stats.unique_views = unique
            stats.save()

            # Create events spread over last 7 days
            for _ in range(min(total, 50)):
                days_ago = random.randint(0, 6)
                hours_ago = random.randint(0, 23)
                ts = now - timedelta(days=days_ago, hours=hours_ago)
                PageViewEvent.objects.create(
                    content_type=ct,
                    object_id=page.pk,
                    timestamp=ts,
                    session_key=f"demo-{random.randint(1000, 9999)}",
                    ip_address=f"192.168.1.{random.randint(1, 254)}",
                    user_agent=random.choice([
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
                        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0)",
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                        "Mozilla/5.0 (Linux; Android 14)",
                    ]),
                    referrer=random.choice([
                        "",
                        "https://google.com/search?q=djinsight",
                        "https://twitter.com/",
                        "https://github.com/krystianmagdziarz/djinsight",
                    ]),
                )

            self.stdout.write(f"  '{page.title}': {total} views, {unique} unique")
