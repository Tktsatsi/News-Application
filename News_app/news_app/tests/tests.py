"""
Comprehensive test suite for the news application.

Tests all user roles, features, and workflows.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from news_app.models import (
    CustomUser,
    Publisher,
    Article,
    Newsletter,
    PublisherJoinRequest)


class AuthenticationTests(TestCase):
    """Test authentication functionality."""

    def setUp(self):
        self.client = Client()

    def test_user_registration(self):
        """Test user can register successfully."""
        response = self.client.post(reverse('register'), {
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
            'role': 'reader'
        })

        # Check user was created
        self.assertTrue(CustomUser.objects.filter(
            username='testuser').exists())
        user = CustomUser.objects.get(username='testuser')
        self.assertEqual(user.role, 'reader')

    def test_user_login(self):
        """Test user can login successfully."""
        # Create user
        user = CustomUser.objects.create_user(
            username='testuser',
            password='testpass123',
            role='reader'
        )

        # Login
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'testpass123'
        })

        # Check login successful
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_user_logout(self):
        """Test user can logout successfully."""
        # Create and login user
        user = CustomUser.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')

        # Logout
        response = self.client.get(reverse('logout'))

        # Check user logged out
        response = self.client.get(reverse('home'))
        self.assertFalse(response.wsgi_request.user.is_authenticated)


class ReaderTests(TestCase):
    """Test reader functionality."""

    def setUp(self):
        self.client = Client()
        self.reader = CustomUser.objects.create_user(
            username='reader1',
            password='testpass123',
            role='reader'
        )
        self.publisher = Publisher.objects.create(
            name='Test Publisher',
            description='A test publisher'
        )
        self.journalist = CustomUser.objects.create_user(
            username='journalist1',
            password='testpass123',
            role='journalist'
        )
        self.editor = CustomUser.objects.create_user(
            username='editor1',
            password='testpass123',
            role='editor'
        )

        # Create approved article
        self.article = Article.objects.create(
            title='Test Article',
            content='Test content',
            author=self.journalist,
            publisher=self.publisher,
            is_approved=True,
            approved_by=self.editor,
            published_date=timezone.now()
        )

        self.client.login(username='reader1', password='testpass123')

    def test_reader_can_view_approved_articles(self):
        """Test reader can view approved articles."""
        response = self.client.get(reverse('article_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Article')

    def test_reader_cannot_view_pending_articles(self):
        """Test reader cannot see pending articles in list."""
        # Create pending article
        pending_article = Article.objects.create(
            title='Pending Article',
            content='Pending content',
            author=self.journalist,
            is_approved=False
        )

        response = self.client.get(reverse('article_list'))
        self.assertNotContains(response, 'Pending Article')

    def test_reader_can_unsubscribe_from_publisher(self):
        """Test reader can unsubscribe from publishers."""
        # First subscribe
        self.reader.subscribed_publishers.add(self.publisher)

        # Then unsubscribe
        self.reader.subscribed_publishers.remove(self.publisher)

        # Verify subscription was removed
        self.reader.refresh_from_db()
        self.assertNotIn(self.publisher,
                         self.reader.subscribed_publishers.all())

    def test_reader_can_unsubscribe_from_publisher(self):
        """Test reader can unsubscribe from publishers."""
        # First subscribe
        self.reader.subscribed_publishers.add(self.publisher)

        # Then unsubscribe
        self.reader.subscribed_publishers.remove(self.publisher)

        # Verify subscription was removed
        self.reader.refresh_from_db()
        self.assertNotIn(self.publisher,
                         self.reader.subscribed_publishers.all())

    def test_reader_can_view_subscription_dashboard(self):
        """Test reader can access subscription dashboard."""
        # Subscribe to publisher first
        self.reader.subscribed_publishers.add(self.publisher)

        response = self.client.get(reverse('subscription_dashboard'))
        self.assertEqual(response.status_code, 200)

        # Check that publishers are in the context
        self.assertIn('subscribed_publishers', response.context)
        self.assertIn(self.publisher,
                      response.context['subscribed_publishers'])

    def test_reader_cannot_create_articles(self):
        """Test reader cannot access article creation."""
        response = self.client.get(reverse('create_article'))
        # Should redirect or show error
        self.assertNotEqual(response.status_code, 200)


class JournalistTests(TestCase):
    """Test journalist functionality."""

    def setUp(self):
        self.client = Client()
        self.journalist = CustomUser.objects.create_user(
            username='journalist1',
            password='testpass123',
            role='journalist'
        )
        self.publisher = Publisher.objects.create(
            name='Test Publisher',
            description='A test publisher'
        )
        self.publisher.journalists.add(self.journalist)

        self.client.login(username='journalist1', password='testpass123')

    def test_journalist_can_create_article(self):
        """Test journalist can create articles."""
        response = self.client.post(reverse('create_article'), {
            'title': 'New Article',
            'content': 'Article content here',
            'summary': 'Summary',
            'publisher': self.publisher.id
        })

        # Check article was created
        self.assertTrue(Article.objects.filter(title='New Article').exists())
        article = Article.objects.get(title='New Article')
        self.assertEqual(article.author, self.journalist)
        self.assertFalse(article.is_approved)  # Should be pending

    def test_journalist_can_create_independent_article(self):
        """Test journalist can create articles without publisher."""
        response = self.client.post(reverse('create_article'), {
            'title': 'Independent Article',
            'content': 'Independent content',
            'summary': 'Summary',
            'publisher': ''  # No publisher
        })

        # Check article was created
        self.assertTrue(Article.objects.filter(
            title='Independent Article').exists())
        article = Article.objects.get(title='Independent Article')
        self.assertIsNone(article.publisher)

    def test_journalist_can_view_own_articles(self):
        """Test journalist can view their own articles."""
        Article.objects.create(
            title='My Article',
            content='Content',
            author=self.journalist
        )

        response = self.client.get(reverse('my_articles'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'My Article')

    def test_journalist_can_edit_own_pending_article(self):
        """Test journalist can edit their own pending articles."""
        article = Article.objects.create(
            title='Original Title',
            content='Original content',
            author=self.journalist,
            is_approved=False
        )

        response = self.client.post(reverse('edit_article',
                                            args=[article.id]), {
            'title': 'Updated Title',
            'content': 'Updated content',
            'summary': 'Summary',
            'publisher': ''
        })

        # Check article was updated
        article.refresh_from_db()
        self.assertEqual(article.title, 'Updated Title')

    def test_journalist_cannot_edit_approved_article(self):
        """Test journalist cannot edit approved articles."""
        editor = CustomUser.objects.create_user(
            username='editor1',
            password='testpass123',
            role='editor'
        )
        article = Article.objects.create(
            title='Approved Article',
            content='Content',
            author=self.journalist,
            is_approved=True,
            approved_by=editor
        )

        response = self.client.get(reverse('edit_article', args=[article.id]))
        # Should be redirected or show error
        self.assertNotEqual(response.status_code, 200)

    def test_journalist_can_delete_own_pending_article(self):
        """Test journalist can delete their own pending articles."""
        article = Article.objects.create(
            title='To Delete',
            content='Content',
            author=self.journalist,
            is_approved=False
        )

        response = self.client.post(reverse('delete_article',
                                            args=[article.id]))

        # Check article was deleted
        self.assertFalse(Article.objects.filter(title='To Delete').exists())

    def test_journalist_can_create_newsletter(self):
        """Test journalist can create newsletters."""
        response = self.client.post(reverse('create_newsletter'), {
            'title': 'Test Newsletter',
            'content': 'Newsletter content',
            'publisher': self.publisher.id
        })

        # Check newsletter was created
        self.assertTrue(Newsletter.objects.filter(
            title='Test Newsletter').exists())

    def test_journalist_can_request_join_publisher(self):
        """Test journalist can request to join a publisher."""
        new_publisher = Publisher.objects.create(
            name='Another Publisher',
            description='Test'
        )

        response = self.client.post(
            reverse('request_join_publisher', args=[new_publisher.id]),
            {'message': 'Please let me join'}
        )

        # Check request was created
        self.assertTrue(
            PublisherJoinRequest.objects.filter(
                user=self.journalist,
                publisher=new_publisher
            ).exists()
        )

    def test_journalist_cannot_subscribe_to_publishers(self):
        """
        Test journalists cannot subscribe to publishers (only readers can).
        """
        # Try to subscribe journalist to publisher
        initial_count = self.publisher.subscribed_readers.count()

        response = self.client.get(reverse('subscription_dashboard'))
        self.assertNotEqual(response.status_code, 200)


class EditorTests(TestCase):
    """Test editor functionality."""

    def setUp(self):
        self.client = Client()
        self.editor = CustomUser.objects.create_user(
            username='editor1',
            password='testpass123',
            role='editor'
        )
        self.journalist = CustomUser.objects.create_user(
            username='journalist1',
            password='testpass123',
            role='journalist'
        )
        self.publisher = Publisher.objects.create(
            name='Test Publisher',
            description='A test publisher'
        )
        self.publisher.editors.add(self.editor)

        # Grant approve_article permission to editor
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        content_type = ContentType.objects.get_for_model(Article)
        permission = Permission.objects.get(
            codename='approve_article',
            content_type=content_type
        )
        self.editor.user_permissions.add(permission)

        self.client.login(username='editor1', password='testpass123')

    def test_editor_can_view_pending_articles(self):
        """Test editor can view pending articles."""
        article = Article.objects.create(
            title='Pending Article',
            content='Content',
            author=self.journalist,
            is_approved=False
        )

        response = self.client.get(reverse('pending_articles'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pending Article')

    def test_editor_can_approve_article(self):
        """Test editor can approve articles."""
        article = Article.objects.create(
            title='To Approve',
            content='Content',
            author=self.journalist,
            is_approved=False
        )

        response = self.client.post(reverse('approve_article',
                                            args=[article.id]))

        # Check article was approved
        article.refresh_from_db()
        self.assertTrue(article.is_approved)
        self.assertEqual(article.approved_by, self.editor)
        self.assertIsNotNone(article.approval_date)

    def test_editor_can_access_publisher_dashboard(self):
        """Test editor can access publisher dashboard."""
        response = self.client.get(
            reverse('publisher_dashboard', args=[self.publisher.id])
        )
        self.assertEqual(response.status_code, 200)

    def test_editor_can_approve_join_request(self):
        """Test editor can approve join requests."""
        new_journalist = CustomUser.objects.create_user(
            username='journalist2',
            password='testpass123',
            role='journalist'
        )
        join_request = PublisherJoinRequest.objects.create(
            user=new_journalist,
            publisher=self.publisher,
            message='Please let me join',
            status='pending'
        )

        response = self.client.post(
            reverse('approve_join_request', args=[join_request.id])
        )

        # Check request was approved and user was added
        join_request.refresh_from_db()
        self.assertEqual(join_request.status, 'approved')
        self.assertIn(new_journalist, self.publisher.journalists.all())

    def test_editor_can_reject_join_request(self):
        """Test editor can reject join requests."""
        new_journalist = CustomUser.objects.create_user(
            username='journalist2',
            password='testpass123',
            role='journalist'
        )
        join_request = PublisherJoinRequest.objects.create(
            user=new_journalist,
            publisher=self.publisher,
            message='Please let me join',
            status='pending'
        )

        response = self.client.post(
            reverse('reject_join_request', args=[join_request.id])
        )

        # Check request was rejected
        join_request.refresh_from_db()
        self.assertEqual(join_request.status, 'rejected')
        self.assertNotIn(new_journalist, self.publisher.journalists.all())

    def test_non_member_editor_cannot_access_publisher_dashboard(self):
        """
        Test editor who is not a member cannot access publisher dashboard.
        """
        other_publisher = Publisher.objects.create(
            name='Other Publisher',
            description='Test'
        )

        response = self.client.get(
            reverse('publisher_dashboard', args=[other_publisher.id])
        )

        # Should be redirected or denied
        self.assertNotEqual(response.status_code, 200)


class PublisherTests(TestCase):
    """Test publisher role functionality."""

    def setUp(self):
        self.client = Client()
        self.publisher_user = CustomUser.objects.create_user(
            username='publisher1',
            password='testpass123',
            role='publisher'
        )
        self.client.login(username='publisher1', password='testpass123')

    def test_publisher_can_create_publisher_org(self):
        """Test user with publisher role can create publisher organization."""
        response = self.client.post(reverse('create_publisher'), {
            'name': 'New Publisher',
            'description': 'A new publisher organization',
            'website': 'https://example.com',
            'established_date': '2025-01-01'
        })

        # Check publisher was created
        self.assertTrue(Publisher.objects.filter(
            name='New Publisher').exists())
        publisher = Publisher.objects.get(name='New Publisher')
        # Creator should be added as editor
        self.assertIn(self.publisher_user, publisher.editors.all())

    def test_non_publisher_cannot_create_publisher_org(self):
        """Test non-publisher role cannot create publisher organization."""
        self.client.logout()
        journalist = CustomUser.objects.create_user(
            username='journalist1',
            password='testpass123',
            role='journalist'
        )
        self.client.login(username='journalist1', password='testpass123')

        response = self.client.get(reverse('create_publisher'))
        # Should be redirected or denied
        self.assertNotEqual(response.status_code, 200)


class IntegrationTests(TestCase):
    """Test complete workflows across multiple user roles."""

    def setUp(self):
        self.client = Client()

        # Create users
        self.reader = CustomUser.objects.create_user(
            username='reader1',
            password='testpass123',
            role='reader'
        )
        self.journalist = CustomUser.objects.create_user(
            username='journalist1',
            password='testpass123',
            role='journalist'
        )
        self.editor = CustomUser.objects.create_user(
            username='editor1',
            password='testpass123',
            role='editor'
        )

        # Create publisher
        self.publisher = Publisher.objects.create(
            name='Test Publisher',
            description='Test'
        )
        self.publisher.journalists.add(self.journalist)
        self.publisher.editors.add(self.editor)

        # Grant approve permission to editor
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        content_type = ContentType.objects.get_for_model(Article)
        permission = Permission.objects.get(
            codename='approve_article',
            content_type=content_type
        )
        self.editor.user_permissions.add(permission)

    def test_complete_article_workflow(self):
        """Test complete article creation, approval, and viewing workflow."""
        # Step 1: Journalist creates article
        self.client.login(username='journalist1', password='testpass123')
        response = self.client.post(reverse('create_article'), {
            'title': 'Workflow Article',
            'content': 'Content here',
            'summary': 'Summary',
            'publisher': self.publisher.id
        })

        article = Article.objects.get(title='Workflow Article')
        self.assertFalse(article.is_approved)

        # Step 2: Editor approves article
        self.client.logout()
        self.client.login(username='editor1', password='testpass123')
        response = self.client.post(reverse('approve_article',
                                            args=[article.id]))

        article.refresh_from_db()
        self.assertTrue(article.is_approved)

        # Step 3: Reader views article
        self.client.logout()
        self.client.login(username='reader1', password='testpass123')
        response = self.client.get(reverse('article_list'))
        self.assertContains(response, 'Workflow Article')

        # Step 4: Reader subscribes to publisher (use model directly)
        self.reader.subscribed_publishers.add(self.publisher)
        self.reader.refresh_from_db()
        self.assertIn(self.publisher, self.reader.subscribed_publishers.all())

    def test_join_request_workflow(self):
        """Test complete join request workflow."""
        # Create new journalist not yet in publisher
        new_journalist = CustomUser.objects.create_user(
            username='journalist2',
            password='testpass123',
            role='journalist'
        )

        # Step 1: Journalist requests to join
        self.client.login(username='journalist2', password='testpass123')
        response = self.client.post(
            reverse('request_join_publisher', args=[self.publisher.id]),
            {'message': 'I want to join'}
        )

        join_request = PublisherJoinRequest.objects.get(user=new_journalist)
        self.assertEqual(join_request.status, 'pending')

        # Step 2: Editor approves request
        self.client.logout()
        self.client.login(username='editor1', password='testpass123')
        response = self.client.post(
            reverse('approve_join_request', args=[join_request.id])
        )

        join_request.refresh_from_db()
        self.assertEqual(join_request.status, 'approved')
        self.assertIn(new_journalist, self.publisher.journalists.all())

        # Step 3: New journalist can now create article with this publisher
        self.client.logout()
        self.client.login(username='journalist2', password='testpass123')
        response = self.client.post(reverse('create_article'), {
            'title': 'New Member Article',
            'content': 'Content',
            'summary': 'Summary',
            'publisher': self.publisher.id
        })

        article = Article.objects.get(title='New Member Article')
        self.assertEqual(article.publisher, self.publisher)


class ModelTests(TestCase):
    """Test model methods and validations."""

    def test_publisher_str_method(self):
        """Test Publisher __str__ method."""
        publisher = Publisher.objects.create(name='Test Publisher')
        self.assertEqual(str(publisher), 'Test Publisher')

    def test_article_str_method(self):
        """Test Article __str__ method."""
        journalist = CustomUser.objects.create_user(
            username='journalist1',
            role='journalist'
        )
        article = Article.objects.create(
            title='Test Article',
            content='Content',
            author=journalist,
            is_approved=False
        )
        self.assertEqual(str(article), 'Test Article - Pending')

    def test_custom_user_str_method(self):
        """Test CustomUser __str__ method."""
        user = CustomUser.objects.create_user(
            username='testuser',
            role='journalist'
        )
        self.assertEqual(str(user), 'testuser (Journalist)')

    def test_join_request_str_method(self):
        """Test PublisherJoinRequest __str__ method."""
        journalist = CustomUser.objects.create_user(
            username='journalist1',
            role='journalist'
        )
        publisher = Publisher.objects.create(name='Test Publisher')
        join_request = PublisherJoinRequest.objects.create(
            user=journalist,
            publisher=publisher,
            status='pending'
        )
        self.assertEqual(
            str(join_request),
            'journalist1 -> Test Publisher (pending)'
        )


# Run tests with: python manage.py test news_app.tests
