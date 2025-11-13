"""
Models for the news application.

This module contains all database models including CustomUser, Publisher,
Article, and Newsletter with proper relationships and constraints.
"""

from django.contrib.auth.models import AbstractUser, Group
from django.core.exceptions import ValidationError
from django.db import models


class Publisher(models.Model):
    """
    Publisher model representing news organizations.

    A publisher can have multiple editors and journalists associated with it.
    """

    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    established_date = models.DateField(null=True, blank=True)
    editors = models.ManyToManyField(
        "CustomUser",
        related_name="publisher_editors",
        blank=True,
        limit_choices_to={"role": "editor"},
    )
    journalists = models.ManyToManyField(
        "CustomUser",
        related_name="publisher_journalists",
        blank=True,
        limit_choices_to={"role": "journalist"},
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Meta options for Publisher model."""

        ordering = ["name"]
        verbose_name = "Publisher"
        verbose_name_plural = "Publishers"

    def __str__(self):
        """Return string representation of publisher."""
        return self.name


class CustomUser(AbstractUser):
    """
    Custom user model with role-based fields.

    Extends Django's AbstractUser to include role-specific fields and
    subscription management.
    """

    ROLE_CHOICES = [
        ("reader", "Reader"),
        ("editor", "Editor"),
        ("journalist", "Journalist"),
        ("publisher", "Publisher"),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="reader")

    # Reader-specific fields
    subscribed_publishers = models.ManyToManyField(
        Publisher, related_name="subscribers", blank=True
    )
    subscribed_journalists = models.ManyToManyField(
        "self",
        symmetrical=False,
        related_name="journalist_subscribers",
        blank=True,
        limit_choices_to={"role": "journalist"},
    )

    # Journalist-specific fields are accessed via reverse relations:
    # - independent_articles (from Article.author)
    # - independent_newsletters (from Newsletter.author)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Meta options for CustomUser model."""

        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["username"]

    def __str__(self):
        """Return string representation of user."""
        return f"{self.username} ({self.get_role_display()})"

    def save(self, *args, **kwargs):
        """
        Override save to handle role-based field assignments.

        Sets reader-specific fields to None for journalists and vice versa.
        Also assigns user to appropriate group based on role.
        """
        is_new = self.pk is None
        super().save(*args, **kwargs)

        # Clear inappropriate fields based on role
        if self.role == "journalist":
            self.subscribed_publishers.clear()
            self.subscribed_journalists.clear()
        elif self.role in ["reader", "editor"]:
            # Independent articles and newsletters are handled via
            # reverse relations, no need to clear here
            pass

        # Assign to appropriate group
        if is_new or "role" in kwargs.get("update_fields", []):
            self.groups.clear()
            group_name = self.get_role_display()
            group, created = Group.objects.get_or_create(name=group_name)
            self.groups.add(group)

    def clean(self):
        """Validate that role-specific fields are properly set."""
        super().clean()

        if not self.pk:
            return

        if self.role == "journalist":
            if (
                self.subscribed_publishers.exists()
                or self.subscribed_journalists.exists()
            ):
                raise ValidationError("Journalists cannot have reader subscriptions.")


class Article(models.Model):
    """
    Article model representing news articles.

    Articles must be approved by an editor before publication.
    """

    title = models.CharField(max_length=300)
    content = models.TextField()
    summary = models.TextField(max_length=500, blank=True)
    author = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="independent_articles",
        limit_choices_to={"role": "journalist"},
    )
    publisher = models.ForeignKey(
        Publisher,
        on_delete=models.CASCADE,
        related_name="articles",
        null=True,
        blank=True,
    )
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        related_name="approved_articles",
        null=True,
        blank=True,
        limit_choices_to={"role": "editor"},
    )
    approval_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_date = models.DateTimeField(null=True, blank=True)
    image = models.ImageField(upload_to="article_images/", blank=True, null=True)

    class Meta:
        """Meta options for Article model."""

        ordering = ["-created_at"]
        verbose_name = "Article"
        verbose_name_plural = "Articles"
        permissions = [
            ("approve_article", "Can approve articles"),
        ]

    def __str__(self):
        """Return string representation of article."""
        status = "Approved" if self.is_approved else "Pending"
        return f"{self.title} - {status}"

    def clean(self):
        super().clean()

        # Only check author if it actually exists
        if getattr(self, "author_id", None):
            if self.author.role != "journalist":
                raise ValidationError(
                    "Only users with 'journalist' role can author articles."
                )

        # Only check editor if it actually exists
        if getattr(self, "approved_by_id", None):
            if self.approved_by.role != "editor":
                raise ValidationError(
                    "Only users with 'editor' role can approve articles."
                )


class Newsletter(models.Model):
    """
    Newsletter model representing periodic publications.

    Newsletters can be published by journalists independently or
    through a publisher.
    """

    title = models.CharField(max_length=300)
    content = models.TextField()
    author = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="independent_newsletters",
        limit_choices_to={"role": "journalist"},
    )
    publisher = models.ForeignKey(
        Publisher,
        on_delete=models.CASCADE,
        related_name="newsletters",
        null=True,
        blank=True,
    )
    published_date = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Meta options for Newsletter model."""

        ordering = ["-published_date"]
        verbose_name = "Newsletter"
        verbose_name_plural = "Newsletters"

    def __str__(self):
        """Return string representation of newsletter."""
        return f"{self.title} by {self.author.username}"

    def clean(self):
        """Validate newsletter data."""
        super().clean()

        if self.author and self.author.role != "journalist":
            raise ValidationError(
                "Only users with 'journalist' role can author newsletters."
            )


class PublisherJoinRequest(models.Model):
    """
    Model for managing join requests to publishers.

    Allows journalists and editors to request to join a publisher,
    with approval workflow.
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="publisher_join_requests",
        limit_choices_to={"role__in": ["journalist", "editor"]},
    )
    publisher = models.ForeignKey(
        Publisher, on_delete=models.CASCADE, related_name="join_requests"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    message = models.TextField(blank=True, help_text="Optional message to publisher")
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_join_requests",
    )

    class Meta:
        ordering = ["-created_at"]
        unique_together = ["user", "publisher", "status"]
        verbose_name = "Publisher Join Request"
        verbose_name_plural = "Publisher Join Requests"

    def __str__(self):
        return f"{self.user.username} -> {self.publisher.name} ({self.status})"
