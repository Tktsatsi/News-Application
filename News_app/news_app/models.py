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

    A Publisher represents a news organization that can publish articles
    and newsletters. Publishers have owners, editors, and journalists
    associated with them.

    :ivar name: The name of the publisher (unique)
    :vartype name: CharField
    :ivar description: Optional description of the publisher
    :vartype description: TextField
    :ivar website: Optional website URL
    :vartype website: URLField
    :ivar established_date: Optional date when publisher was established
    :vartype established_date: DateField
    :ivar owner: The user who owns this publisher
    :vartype owner: ForeignKey
    :ivar created_by: The user who created this publisher
    :vartype created_by: ForeignKey
    :ivar editors: Editors associated with this publisher
    :vartype editors: ManyToManyField
    :ivar journalists: Journalists associated with this publisher
    :vartype journalists: ManyToManyField
    :ivar created_at: Timestamp when publisher was created
    :vartype created_at: DateTimeField
    :ivar updated_at: Timestamp when publisher was last updated
    :vartype updated_at: DateTimeField
    """

    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    established_date = models.DateField(null=True, blank=True)

    owner = models.ForeignKey(
        "CustomUser",
        on_delete=models.CASCADE,
        related_name="owned_publishers",
        limit_choices_to={"role": "publisher"},
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        "CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="publishers_created"
    )
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
        ordering = ["name"]
        verbose_name = "Publisher"
        verbose_name_plural = "Publishers"

    def save(self, *args, **kwargs):
        """
        Override save to auto-assign owner if not set.

        If the owner is not set, it will be automatically assigned
        to the user who created the publisher.

        :param args: Variable length argument list
        :param kwargs: Arbitrary keyword arguments
        """
        if not self.owner:
            self.owner = self.created_by
        super().save(*args, **kwargs)

    def __str__(self):
        """
        Return string representation of the publisher.

        :returns: The name of the publisher
        :rtype: str
        """
        return self.name


class CustomUser(AbstractUser):
    """
    Custom user model with role-based fields.

    Extends Django's AbstractUser to include role-specific fields and
    subscription management. Supports four roles: reader, editor,
    journalist, and publisher.

    :ivar role: User's role (reader, editor, journalist, publisher)
    :vartype role: CharField
    :ivar subscribed_newsletters: Newsletters user subscribes to
    :vartype subscribed_newsletters: ManyToManyField
    :ivar subscribed_publishers: Publishers user subscribes to
    :vartype subscribed_publishers: ManyToManyField
    :ivar subscribed_journalists: Journalists user subscribes to
    :vartype subscribed_journalists: ManyToManyField
    :ivar created_at: Timestamp when user was created
    :vartype created_at: DateTimeField
    :ivar updated_at: Timestamp when user was last updated
    :vartype updated_at: DateTimeField

    .. note::
        Journalist-specific content is accessed via reverse relations:
        - independent_articles (from Article.author)
        - independent_newsletters (from Newsletter.author)
    """

    ROLE_CHOICES = [
        ("reader", "Reader"),
        ("editor", "Editor"),
        ("journalist", "Journalist"),
        ("publisher", "Publisher"),
    ]

    role = models.CharField(max_length=20,
                            choices=ROLE_CHOICES,
                            default="reader")

    # Reader-specific fields
    subscribed_newsletters = models.ManyToManyField("Newsletter",
                                                    related_name="subscribers",
                                                    blank=True)

    subscribed_publishers = models.ManyToManyField(
        "Publisher",
        related_name="subscribed_readers",
        blank=True,
        limit_choices_to={"role": "reader"}
    )

    subscribed_journalists = models.ManyToManyField(
        "self",
        symmetrical=False,
        related_name="journalist_subscribers",
        blank=True,
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
        """
        Return string representation of user.

        :returns: Username and role in format "username (Role)"
        :rtype: str
        """
        return f"{self.username} ({self.get_role_display()})"

    def save(self, *args, **kwargs):
        """
        Override save to handle role-based field assignments.

        Clears inappropriate subscription fields based on role and assigns
        user to appropriate Django group based on role.

        :param args: Variable length argument list
        :param kwargs: Arbitrary keyword arguments
        """
        is_new = self.pk is None
        super().save(*args, **kwargs)

        # Clear inappropriate fields based on role
        if self.role == "journalist":
            self.subscribed_newsletters.clear()
            self.subscribed_journalists.clear()
            self.subscribed_publishers.clear()
        elif self.role in ["reader", "editor"]:
            pass

        # Assign to appropriate group
        if is_new or "role" in kwargs.get("update_fields", []):
            self.groups.clear()
            group_name = self.get_role_display()
            group, created = Group.objects.get_or_create(name=group_name)
            self.groups.add(group)

    def clean(self):
        """
        Validate that role-specific fields are properly set.

        :raises ValidationError: If journalist has reader subscriptions
        """
        super().clean()

        if not self.pk:
            return

        if self.role == "journalist":
            if (
                self.subscribed_newsletters.exists()
                or self.subscribed_journalists.exists()
            ):
                raise ValidationError(
                    "Journalists cannot have reader subscriptions.")


class Article(models.Model):
    """
    Article model representing news articles.

    Articles must be approved by an editor before publication, unless
    they are independently published by the journalist.

    :ivar title: The title of the article
    :vartype title: CharField
    :ivar content: The full content of the article
    :vartype content: TextField
    :ivar summary: Optional summary of the article (max 500 chars)
    :vartype summary: TextField
    :ivar author: The journalist who authored the article
    :vartype author: ForeignKey
    :ivar publisher: Optional publisher associated with article
    :vartype publisher: ForeignKey
    :ivar independently_published: Whether article was self-published
    :vartype independently_published: BooleanField
    :ivar is_approved: Whether article has been approved by editor
    :vartype is_approved: BooleanField
    :ivar approved_by: Editor who approved the article
    :vartype approved_by: ForeignKey
    :ivar is_rejected: Whether article has been rejected
    :vartype is_rejected: BooleanField
    :ivar rejected_reason: Reason for rejection if rejected
    :vartype rejected_reason: TextField
    :ivar rejected_by: Editor who rejected the article
    :vartype rejected_by: ForeignKey
    :ivar approval_date: When article was approved
    :vartype approval_date: DateTimeField
    :ivar rejected_date: When article was rejected
    :vartype rejected_date: DateTimeField
    :ivar created_at: When article was created
    :vartype created_at: DateTimeField
    :ivar updated_at: When article was last updated
    :vartype updated_at: DateTimeField
    :ivar published_date: When article was published
    :vartype published_date: DateTimeField
    :ivar image: Optional image for the article
    :vartype image: ImageField
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

    independently_published = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        related_name="approved_articles",
        null=True,
        blank=True,
        limit_choices_to={"role": "editor"},
    )
    is_rejected = models.BooleanField(default=False)
    rejected_reason = models.TextField(blank=True, null=True)
    rejected_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rejected_articles"
    )

    approval_date = models.DateTimeField(null=True, blank=True)
    rejected_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_date = models.DateTimeField(null=True, blank=True)
    image = models.ImageField(upload_to="article_images/",
                              blank=True,
                              null=True)

    class Meta:
        """Meta options for Article model."""

        ordering = ["-created_at"]
        verbose_name = "Article"
        verbose_name_plural = "Articles"
        permissions = [
            ("approve_article", "Can approve articles"),
        ]

    def __str__(self):
        """
        Return string representation of article.

        :returns: Article title and status in format "Title - Status"
        :rtype: str
        """
        status = "Approved" if self.is_approved else "Pending"
        return f"{self.title} - {status}"

    def get_status_display(self):
        """
        Return human-readable status based on approval/rejection state.

        :returns: Status string - "Rejected", "Approved", or "Pending"
        :rtype: str
        """
        if self.is_rejected:
            return "Rejected"
        elif self.is_approved:
            return "Approved"
        else:
            return "Pending"

    @property
    def status(self):
        """
        Return status for CSS class and display.

        :returns: Status string for CSS classes - "rejected",
        "approved", or "pending"
        :rtype: str
        """
        if self.is_rejected:
            return "rejected"
        elif self.is_approved:
            return "approved"
        else:
            return "pending"

    def clean(self):
        """
        Validate article data and relationships.

        Ensures:
            - Author must be a journalist
            - Approver must be an editor
            - Independent articles cannot be approved/rejected by editors

        :raises ValidationError: If validation fails
        """
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

        if self.independently_published:
            if (
                self.is_approved
                or self.is_rejected
                or self.approved_by
                or self.rejected_by
            ):
                raise ValidationError(
                    "Independent articles cannot be approved or rejected "
                    "by an editor."
                )


class Newsletter(models.Model):
    """
    Newsletter model representing periodic publications.

    Newsletters can be published by journalists independently or
    through a publisher. Unlike articles, newsletters do not require
    editor approval.

    :ivar title: The title of the newsletter
    :vartype title: CharField
    :ivar content: The full content of the newsletter
    :vartype content: TextField
    :ivar author: The journalist who authored the newsletter
    :vartype author: ForeignKey
    :ivar publisher: Optional publisher associated with newsletter
    :vartype publisher: ForeignKey
    :ivar published_date: When newsletter was published
    :vartype published_date: DateTimeField
    :ivar created_at: When newsletter was created
    :vartype created_at: DateTimeField
    :ivar updated_at: When newsletter was last updated
    :vartype updated_at: DateTimeField
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
        """
        Return string representation of newsletter.

        :returns: Newsletter title and author in format "Title by username"
        :rtype: str
        """
        return f"{self.title} by {self.author.username}"

    def clean(self):
        """
        Validate newsletter data.

        Ensures the author is a journalist.

        :raises ValidationError: If author is not a journalist
        """
        super().clean()

        if self.author and self.author.role != "journalist":
            raise ValidationError(
                "Only users with 'journalist' role can author newsletters."
            )


class PublisherJoinRequest(models.Model):
    """
    Model representing a request to join a publisher organization.

    Journalists and editors can request to join a publisher. The publisher
    owner can approve or reject these requests.

    :ivar user: The user requesting to join (journalist or editor)
    :vartype user: ForeignKey
    :ivar publisher: The publisher being requested to join
    :vartype publisher: ForeignKey
    :ivar status: Status of the request (pending, approved, rejected)
    :vartype status: CharField
    :ivar message: Optional message from the requester
    :vartype message: TextField
    :ivar created_at: When the request was created
    :vartype created_at: DateTimeField
    :ivar reviewed_at: When the request was reviewed
    :vartype reviewed_at: DateTimeField
    :ivar reviewed_by: User who reviewed the request
    :vartype reviewed_by: ForeignKey

    .. note::
        There can only be one pending request per user-publisher pair.
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
        Publisher, on_delete=models.CASCADE, related_name="join_requests",
    )

    status = models.CharField(max_length=20,
                              choices=STATUS_CHOICES,
                              default="pending")
    message = models.TextField(blank=True)
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
        constraints = [
            models.UniqueConstraint(
                fields=["user", "publisher"],
                condition=models.Q(status="pending"),
                name="unique_pending_join_request",
            )
        ]

    def __str__(self):
        """
        Return string representation of join request.

        :returns: Request details in format
        "username -> Publisher Name (status)"
        :rtype: str
        """
        return f"{self.user.username} -> {self.publisher.name} ({self.status})"
