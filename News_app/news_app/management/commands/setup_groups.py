"""
Management command to set up user groups with appropriate permissions.

This command creates Reader, Editor, and Journalist groups and assigns
the appropriate permissions to each group based on their role.
"""

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from news_app.models import Article, Newsletter


class Command(BaseCommand):
    """Management command to set up user groups with permissions."""

    help = "Create user groups and assign permissions"

    def handle(self, *args, **kwargs):
        """Execute the command to create groups and permissions."""
        self.stdout.write("Setting up user groups and permissions...")

        # Get content types
        article_ct = ContentType.objects.get_for_model(Article)
        newsletter_ct = ContentType.objects.get_for_model(Newsletter)

        # Create or get groups
        reader_group, created = Group.objects.get_or_create(name="Reader")
        if created:
            self.stdout.write(self.style.SUCCESS("Created Reader group"))

        editor_group, created = Group.objects.get_or_create(name="Editor")
        if created:
            self.stdout.write(self.style.SUCCESS("Created Editor group"))

        journalist_group, created = Group.objects.get_or_create(name="Journalist")
        if created:
            self.stdout.write(self.style.SUCCESS("Created Journalist group"))

        # Clear existing permissions
        reader_group.permissions.clear()
        editor_group.permissions.clear()
        journalist_group.permissions.clear()

        # Reader permissions - can only view
        reader_permissions = Permission.objects.filter(
            content_type__in=[article_ct, newsletter_ct],
            codename__startswith="view_"
        )
        reader_group.permissions.set(reader_permissions)
        self.stdout.write(
            self.style.SUCCESS(
                f"Assigned {reader_permissions.count()} " f"permissions to Reader group"
            )
        )

        # Editor permissions - can view, change, delete, and approve
        editor_permissions = Permission.objects.filter(
            content_type__in=[article_ct, newsletter_ct],
            codename__in=[
                "view_article",
                "change_article",
                "delete_article",
                "approve_article",
                "view_newsletter",
                "change_newsletter",
                "delete_newsletter",
            ],
        )
        editor_group.permissions.set(editor_permissions)
        self.stdout.write(
            self.style.SUCCESS(
                f"Assigned {editor_permissions.count()} " f"permissions to Editor group"
            )
        )

        # Journalist permissions - can create, view, change, delete
        journalist_permissions = Permission.objects.filter(
            content_type__in=[article_ct, newsletter_ct],
            codename__in=[
                "add_article",
                "view_article",
                "change_article",
                "delete_article",
                "add_newsletter",
                "view_newsletter",
                "change_newsletter",
                "delete_newsletter",
            ],
        )
        journalist_group.permissions.set(journalist_permissions)
        self.stdout.write(
            self.style.SUCCESS(
                f"Assigned {journalist_permissions.count()} "
                f"permissions to Journalist group"
            )
        )

        self.stdout.write(self.style.SUCCESS("Successfully set up all groups!"))
