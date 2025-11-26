"""
Unit tests for news_app REST API.

This module contains tests for API endpoints including articles,
newsletters, publishers, and subscription-based article retrieval.
"""

from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from news_app.models import Article, CustomUser, Newsletter, Publisher


class ArticleAPITest(APITestCase):
    """Test cases for Article API endpoints."""

    def setUp(self):
        """Set up test data and authentication."""
        self.journalist = CustomUser.objects.create_user(
            username="journalist1", password="testpass123", role="journalist"
        )
        self.editor = CustomUser.objects.create_user(
            username="editor1", password="testpass123", role="editor"
        )
        self.reader = CustomUser.objects.create_user(
            username="reader1", password="testpass123", role="reader"
        )

        self.journalist_token = Token.objects.create(user=self.journalist)
        self.editor_token = Token.objects.create(user=self.editor)
        self.reader_token = Token.objects.create(user=self.reader)

        self.publisher = Publisher.objects.create(name="Test Publisher")

        self.approved_article = Article.objects.create(
            title="Approved Article",
            content="This is approved content",
            author=self.journalist,
            publisher=self.publisher,
            is_approved=True,
            approved_by=self.editor,
        )

    def test_list_articles_authenticated(self):
        """Test authenticated users can list articles."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {self.reader_token.key}")
        url = reverse("api-article-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_list_articles_unauthenticated(self):
        """Test unauthenticated users cannot list articles."""
        url = reverse("api-article-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_article_as_journalist(self):
        """Test journalists can create articles."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {self.journalist_token.key}")
        url = reverse("api-article-list")
        data = {
            "title": "New Article",
            "content": "New article content",
            "summary": "Summary",
            "publisher": self.publisher.id,
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Article.objects.count(), 2)

    def test_create_article_as_reader_fails(self):
        """Test readers cannot create articles."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {self.reader_token.key}")
        url = reverse("api-article-list")
        data = {
            "title": "New Article",
            "content": "New article content",
            "summary": "Summary",
            "publisher": self.publisher.id,
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_article_as_editor(self):
        """Test editors can update articles."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {self.editor_token.key}")
        url = reverse("api-article-detail", args=[self.approved_article.id])
        data = {
            "title": "Updated Title",
            "content": "Updated content",
            "summary": "Updated summary",
            "publisher": self.publisher.id,
        }
        response = self.client.patch(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.approved_article.refresh_from_db()
        self.assertEqual(self.approved_article.title, "Updated Title")

    def test_delete_article_as_editor(self):
        """Test editors can delete articles."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {self.editor_token.key}")
        url = reverse("api-article-detail", args=[self.approved_article.id])
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Article.objects.count(), 0)


class PublisherAPITest(APITestCase):
    """Test cases for Publisher API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.user = CustomUser.objects.create_user(
            username="user1", password="testpass123", role="reader"
        )
        self.token = Token.objects.create(user=self.user)

        self.publisher = Publisher.objects.create(
            name="Test Publisher", description="Test description"
        )

    def test_list_publishers(self):
        """Test listing publishers."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        url = reverse("api-publisher-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_retrieve_publisher(self):
        """Test retrieving a single publisher."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        url = reverse("api-publisher-detail", args=[self.publisher.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Test Publisher")


class JournalistArticlesAPITest(APITestCase):
    """Test cases for journalist articles endpoint."""

    def setUp(self):
        """Set up test data."""
        self.journalist = CustomUser.objects.create_user(
            username="journalist1", password="testpass123", role="journalist"
        )
        self.user = CustomUser.objects.create_user(
            username="user1", password="testpass123", role="reader"
        )
        self.token = Token.objects.create(user=self.user)

        self.article1 = Article.objects.create(
            title="Article 1",
            content="Content 1",
            author=self.journalist,
            is_approved=True,
        )
        self.article2 = Article.objects.create(
            title="Article 2",
            content="Content 2",
            author=self.journalist,
            is_approved=True,
        )

    def test_get_journalist_articles(self):
        """Test retrieving articles by journalist."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        url = reverse("journalist-articles", args=[self.journalist.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)


class SubscriptionArticlesAPITest(APITestCase):
    """Test cases for subscription-based article retrieval."""

    def setUp(self):
        """Set up test data."""
        self.reader = CustomUser.objects.create_user(
            username="reader1",
            password="testpass123",
            role="reader",
            email="reader@test.com",
        )
        self.journalist1 = CustomUser.objects.create_user(
            username="journalist1", password="testpass123", role="journalist"
        )
        self.journalist2 = CustomUser.objects.create_user(
            username="journalist2", password="testpass123", role="journalist"
        )

        self.token = Token.objects.create(user=self.reader)

        self.publisher1 = Publisher.objects.create(name="Publisher 1")
        self.publisher2 = Publisher.objects.create(name="Publisher 2")

        # Subscribe reader to publisher1 and journalist1
        self.reader.subscribed_publishers.add(self.publisher1)
        self.reader.subscribed_journalists.add(self.journalist1)

        # Create articles
        self.article1 = Article.objects.create(
            title="Article from subscribed publisher",
            content="Content",
            author=self.journalist2,
            publisher=self.publisher1,
            is_approved=True,
        )
        self.article2 = Article.objects.create(
            title="Article from subscribed journalist",
            content="Content",
            author=self.journalist1,
            is_approved=True,
        )
        self.article3 = Article.objects.create(
            title="Article from unsubscribed",
            content="Content",
            author=self.journalist2,
            publisher=self.publisher2,
            is_approved=True,
        )

    def test_get_subscription_articles(self):
        """Test retrieving articles based on subscriptions."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        url = reverse("subscription-articles")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return 2 articles (from subscribed publisher and journalist)
        self.assertEqual(len(response.data["results"]), 2)

        # Verify correct articles are returned
        titles = [article["title"] for article in response.data["results"]]
        self.assertIn("Article from subscribed publisher", titles)
        self.assertIn("Article from subscribed journalist", titles)
        self.assertNotIn("Article from unsubscribed", titles)

    def test_subscription_articles_non_reader_role(self):
        """Test non-reader roles get empty results."""
        journalist_token = Token.objects.create(user=self.journalist1)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {journalist_token.key}")
        url = reverse("subscription-articles")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)

    def test_subscription_articles_no_subscriptions(self):
        """Test reader with no subscriptions gets no articles."""
        reader2 = CustomUser.objects.create_user(
            username="reader2", password="testpass123", role="reader"
        )
        token2 = Token.objects.create(user=reader2)

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token2.key}")
        url = reverse("subscription-articles")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)


class NewsletterAPITest(APITestCase):
    """Test cases for Newsletter API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.journalist = CustomUser.objects.create_user(
            username="journalist1", password="testpass123", role="journalist"
        )
        self.editor = CustomUser.objects.create_user(
            username="editor1", password="testpass123", role="editor"
        )

        self.journalist_token = Token.objects.create(user=self.journalist)
        self.editor_token = Token.objects.create(user=self.editor)

        self.publisher = Publisher.objects.create(name="Test Publisher")

        self.newsletter = Newsletter.objects.create(
            title="Test Newsletter",
            content="Newsletter content",
            author=self.journalist,
            publisher=self.publisher,
        )

    def test_list_newsletters(self):
        """Test listing newsletters."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {self.journalist_token.key}")
        url = reverse("api-newsletter-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_create_newsletter_as_journalist(self):
        """Test journalists can create newsletters."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {self.journalist_token.key}")
        url = reverse("api-newsletter-list")
        data = {
            "title": "New Newsletter",
            "content": "Newsletter content",
            "publisher": self.publisher.id,
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Newsletter.objects.count(), 2)
