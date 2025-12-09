from django.apps import AppConfig


class BlogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "blog"

    def ready(self):
        try:
            from blog.models import Post
            from djinsight.models import ContentTypeRegistry

            ContentTypeRegistry.register(Post)
        except Exception:
            # Database not ready yet (e.g., during migrations)
            pass
