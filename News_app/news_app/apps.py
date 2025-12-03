"""News application configuration."""

from django.apps import AppConfig


class NewsAppConfig(AppConfig):
    """
    Configuration for the news_app application.

    Django app configuration that handles app initialization and
    signal registration.

    :ivar default_auto_field: Default primary key field type
    :ivar name: Application name
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "news_app"

    def ready(self):
        """
        Import signal handlers when the app is ready.

        This method is called when Django starts and ensures that
        signal handlers are registered.
        """
        # Explicitly import signal handlers to ensure they are registered
        from . import signals  # noqa: F401
