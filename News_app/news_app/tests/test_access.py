from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model

from news_app.models import Article, Newsletter


User = get_user_model()


class AccessControlTests(TestCase):
    def setUp(self):
        # create users
        self.journalist = User.objects.create_user(
            username="journalist",
            password="journalistpass",
            role="journalist",
        )
        self.reader = User.objects.create_user(
            username="reader",
            password="readerpass",
            role="reader",
        )

        # create an approved article
        self.article = Article.objects.create(
            title="Test Article",
            content="This is the full content of the article.",
            summary="This is the summary of the article.",
            author=self.journalist,
            is_approved=True,
            published_date=timezone.now(),
        )

        # create a newsletter
        self.newsletter = Newsletter.objects.create(
            title="Test Newsletter",
            content="Newsletter full content.",
            author=self.journalist,
        )

    def test_anonymous_list_shows_only_titles(self):
        url = reverse("article_list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        # title must be visible
        self.assertContains(resp, "Test Article")
        # summary and read-more link should not be visible to anonymous users
        self.assertNotContains(resp, "This is the summary of the article.")
        self.assertNotContains(resp, "Read More")

    def test_authenticated_list_shows_full_item(self):
        self.client.login(username="reader", password="readerpass")
        url = reverse("article_list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        # authenticated user should see the summary and read-more
        self.assertContains(resp, "This is the summary of the article.")
        self.assertContains(resp, "Read More")

    def test_anonymous_article_detail_redirects(self):
        url = reverse("article_detail", args=[self.article.pk])
        resp = self.client.get(url)
        # LoginRequiredMixin should redirect anonymous users
        self.assertIn(resp.status_code, (301, 302))
        self.assertIn("login", resp.url)

    def test_anonymous_newsletter_detail_redirects(self):
        url = reverse("newsletter_detail", args=[self.newsletter.pk])
        resp = self.client.get(url)
        self.assertIn(resp.status_code, (301, 302))
        self.assertIn("login", resp.url)
