"""
Serializers for the news application REST API.

This module contains serializers that convert Django models to/from
JSON and XML formats for API interaction.
"""

from rest_framework import serializers

from .models import Article, CustomUser, Newsletter, Publisher


class PublisherSerializer(serializers.ModelSerializer):
    """
    Serializer for Publisher model.

    Converts Publisher instances to JSON/XML format for API responses.
    Includes all publisher fields except relationships.

    :ivar Meta: Serializer metadata including model and fields
    """

    class Meta:
        """Meta options for PublisherSerializer."""

        model = Publisher
        fields = [
            "id",
            "name",
            "description",
            "website",
            "established_date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for CustomUser model.

    Provides basic user information for API responses.
    Excludes sensitive fields like password and authentication tokens.

    :ivar Meta: Serializer metadata including model and fields
    """

    class Meta:
        """Meta options for UserSerializer."""

        model = CustomUser
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
        ]
        read_only_fields = ["id", "role"]


class ArticleSerializer(serializers.ModelSerializer):
    """
    Serializer for Article model.

    Converts Article instances to JSON/XML format, including nested
    author and publisher information. Used for read operations.

    :ivar author: Nested UserSerializer for article author
    :ivar publisher: Nested PublisherSerializer for article publisher
    :ivar approved_by: Nested UserSerializer for approving editor
    :ivar Meta: Serializer metadata including model and fields
    """

    author = UserSerializer(read_only=True)
    publisher = PublisherSerializer(read_only=True)
    approved_by = UserSerializer(read_only=True)

    class Meta:
        """Meta options for ArticleSerializer."""

        model = Article
        fields = [
            "id",
            "title",
            "content",
            "summary",
            "author",
            "publisher",
            "is_approved",
            "approved_by",
            "approval_date",
            "created_at",
            "updated_at",
            "published_date",
        ]
        read_only_fields = [
            "id",
            "is_approved",
            "approved_by",
            "approval_date",
            "created_at",
            "updated_at",
            "published_date",
        ]


class ArticleCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating Article instances.

    Used by journalists to create new articles.
    Automatically sets the author to the current user from request context.

    :ivar Meta: Serializer metadata including model and fields
    """

    class Meta:
        """Meta options for ArticleCreateSerializer."""

        model = Article
        fields = [
            "title",
            "content",
            "summary",
            "publisher",
        ]

    def create(self, validated_data):
        """
        Create a new article with the current user as author.

        Automatically assigns the authenticated user as the article author.

        :param validated_data: Validated data from the serializer
        :type validated_data: dict
        :returns: The created article instance with author set
        :rtype: Article
        """
        validated_data["author"] = self.context["request"].user
        return super().create(validated_data)


class NewsletterSerializer(serializers.ModelSerializer):
    """
    Serializer for Newsletter model.

    Converts Newsletter instances to JSON/XML format, including nested
    author and publisher information. Used for read operations.

    :ivar author: Nested UserSerializer for newsletter author
    :ivar publisher: Nested PublisherSerializer for newsletter publisher
    :ivar Meta: Serializer metadata including model and fields
    """

    author = UserSerializer(read_only=True)
    publisher = PublisherSerializer(read_only=True)

    class Meta:
        """Meta options for NewsletterSerializer."""

        model = Newsletter
        fields = [
            "id",
            "title",
            "content",
            "author",
            "publisher",
            "published_date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "published_date",
            "created_at",
            "updated_at",
        ]


class NewsletterCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating Newsletter instances.

    Used by journalists to create new newsletters.
    Automatically sets the author to the current user from request context.

    :ivar Meta: Serializer metadata including model and fields
    """

    class Meta:
        """Meta options for NewsletterCreateSerializer."""

        model = Newsletter
        fields = [
            "title",
            "content",
            "publisher",
        ]

    def create(self, validated_data):
        """
        Create a new newsletter with the current user as author.

        Args:
            validated_data: Validated data from the serializer.

        Returns:
            Newsletter: The created newsletter instance.
        """
        validated_data["author"] = self.context["request"].user
        return super().create(validated_data)


class SubscriptionArticleSerializer(serializers.ModelSerializer):
    """
    Serializer for articles based on user subscriptions.

    Returns only approved articles from publishers and journalists
    that the user is subscribed to. All fields are read-only.

    :ivar author: Nested UserSerializer for article author
    :ivar publisher: Nested PublisherSerializer for article publisher
    :ivar Meta: Serializer metadata including model and fields
    """

    author = UserSerializer(read_only=True)
    publisher = PublisherSerializer(read_only=True)

    class Meta:
        """Meta options for SubscriptionArticleSerializer."""

        model = Article
        fields = [
            "id",
            "title",
            "content",
            "summary",
            "author",
            "publisher",
            "published_date",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "title",
            "content",
            "summary",
            "author",
            "publisher",
            "published_date",
            "created_at",
        ]
