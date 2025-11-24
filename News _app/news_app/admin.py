"""
Django admin configuration for news_app models.

This module registers models with the Django admin interface and
configures their display and editing options.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Article, CustomUser, Newsletter, Publisher


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    """Admin interface for CustomUser model."""

    list_display = [
        "username",
        "email",
        "role",
        "is_staff",
        "is_active",
    ]
    list_filter = ["role", "is_staff", "is_active"]
    search_fields = ["username", "email", "first_name", "last_name"]

    fieldsets = BaseUserAdmin.fieldsets + (
        ("Role Information", {"fields": ("role",)}),
        (
            "Subscriptions (Reader)",
            {
                "fields": ("subscribed_newsletters", "subscribed_journalists"),
                "description": "Only applicable for users with Reader role",
            },
        ),
    )

    filter_horizontal = (
        "groups",
        "user_permissions",
        "subscribed_newsletters",
        "subscribed_journalists",
    )


@admin.register(Publisher)
class PublisherAdmin(admin.ModelAdmin):
    """Admin interface for Publisher model."""

    list_display = ["name", "website", "established_date", "created_at"]
    search_fields = ["name", "description"]
    filter_horizontal = ["editors", "journalists"]
    list_filter = ["created_at"]
    date_hierarchy = "created_at"


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    """Admin interface for Article model."""

    list_display = [
        "title",
        "author",
        "publisher",
        "is_approved",
        "approved_by",
        "created_at",
        "published_date",
    ]
    list_filter = ["is_approved", "created_at", "approval_date"]
    search_fields = ["title", "content", "author__username"]
    date_hierarchy = "created_at"
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (
            "Article Information",
            {"fields": ("title", "summary", "content", "author", "publisher")},
        ),
        (
            "Approval Status",
            {
                "fields": (
                    "is_approved",
                    "approved_by",
                    "approval_date",
                    "published_date",
                )
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(Newsletter)
class NewsletterAdmin(admin.ModelAdmin):
    """Admin interface for Newsletter model."""

    list_display = [
        "title",
        "author",
        "publisher",
        "published_date",
        "created_at",
    ]
    list_filter = ["published_date", "created_at"]
    search_fields = ["title", "content", "author__username"]
    date_hierarchy = "published_date"
    readonly_fields = ["published_date", "created_at", "updated_at"]

    fieldsets = (
        (
            "Newsletter Information",
            {"fields": ("title", "content", "author", "publisher")},
        ),
        (
            "Timestamps",
            {
                "fields": ("published_date", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )
