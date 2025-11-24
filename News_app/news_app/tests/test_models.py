"""
Unit tests for news_app models.

This module contains tests for all model classes including CustomUser,
Publisher, Article, and Newsletter.
"""

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import TestCase

from news_app.models import Article, CustomUser, Newsletter, Publisher


class PublisherModelTest(TestCase):
    """Test cases for Publisher model."""

    def setUp(self):
        """Set up test data."""
        self.publisher = Publisher.objects.create(
            name="Test Publisher",
            description="A test publisher",
            website="https://testpublisher.com",
        )

    def test_publisher_creation(self):
        """Test publisher is created successfully."""
        self.assertEqual(self.publisher.name, "Test Publisher")
        self.assertEqual(str(self.publisher), "Test Publisher")

    def test_publisher_unique_name(self):
        """Test publisher name is unique."""
        with self.assertRaises(Exception):
            Publisher.objects.create(name="Test Publisher")


class CustomUserModelTest(TestCase):
    """Test cases for CustomUser model."""

    def setUp(self):
        """Set up test data."""
        self.reader = CustomUser.objects.create_user(
            username="reader1", password="testpass123", role="reader"
        )
        self.editor = CustomUser.objects.create_user(
            username="editor1", password="testpass123", role="editor"
        )
        self.journalist = CustomUser.objects.create_user(
            username="journalist1", password="testpass123", role="journalist"
        )

    def test_user_creation_with_roles(self):
        """Test users are created with correct roles."""
        self.assertEqual(self.reader.role, "reader")
        self.assertEqual(self.editor.role, "editor")
        self.assertEqual(self.journalist.role, "journalist")

    def test_user_string_representation(self):
        """Test user string representation includes role."""
        self.assertEqual(str(self.reader), "reader1 (Reader)")

    def test_user_assigned_to_group(self):
        """Test user is automatically assigned to correct group."""
        reader_group = Group.objects.get(name="Reader")
        self.assertIn(reader_group, self.reader.groups.all())

    def test_journalist_cannot_have_subscriptions(self):
        """Test journalist role clears subscription fields."""
        publisher = Publisher.objects.create(name="Test Pub")
        self.journalist.subscribed_publishers.add(publisher)
        self.journalist.save()

        self.assertEqual(self.journalist.subscribed_publishers.count(), 0)


class ArticleModelTest(TestCase):
    """Test cases for Article model."""

    def setUp(self):
        """Set up test data."""
        self.journalist = CustomUser.objects.create_user(
            username="journalist1", password="testpass123", role="journalist"
        )
        self.editor = CustomUser.objects.create_user(
            username="editor1", password="testpass123", role="editor"
        )
        self.publisher = Publisher.objects.create(name="Test Publisher")
        self.article = Article.objects.create(
            title="Test Article",
            content="This is test content",
            summary="Test summary",
            author=self.journalist,
            publisher=self.publisher,
        )

    def test_article_creation(self):
        """Test article is created successfully."""
        self.assertEqual(self.article.title, "Test Article")
        self.assertFalse(self.article.is_approved)
        self.assertEqual(str(self.article), "Test Article - Pending")

    def test_article_approval(self):
        """Test article approval process."""
        self.article.is_approved = True
        self.article.approved_by = self.editor
        self.article.save()

        self.assertTrue(self.article.is_approved)
        self.assertEqual(self.article.approved_by, self.editor)

    def test_article_requires_journalist_author(self):
        """Test article author must be a journalist."""
        reader = CustomUser.objects.create_user(
            username="reader1", password="testpass123", role="reader"
        )
        article = Article(title="Invalid Article",
                          content="Content",
                          author=reader)
        with self.assertRaises(ValidationError):
            article.full_clean()


class NewsletterModelTest(TestCase):
    """Test cases for Newsletter model."""

    def setUp(self):
        """Set up test data."""
        self.journalist = CustomUser.objects.create_user(
            username="journalist1", password="testpass123", role="journalist"
        )
        self.publisher = Publisher.objects.create(name="Test Publisher")
        self.newsletter = Newsletter.objects.create(
            title="Test Newsletter",
            content="Newsletter content",
            author=self.journalist,
            publisher=self.publisher,
        )

    def test_newsletter_creation(self):
        """Test newsletter is created successfully."""
        self.assertEqual(self.newsletter.title, "Test Newsletter")
        self.assertEqual(str(self.newsletter),
                         "Test Newsletter by journalist1")

    def test_newsletter_requires_journalist_author(self):
        """Test newsletter author must be a journalist."""
        reader = CustomUser.objects.create_user(
            username="reader1", password="testpass123", role="reader"
        )
        newsletter = Newsletter(
            title="Invalid Newsletter", content="Content", author=reader
        )
        with self.assertRaises(ValidationError):
            newsletter.full_clean()
