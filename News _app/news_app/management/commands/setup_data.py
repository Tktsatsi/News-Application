"""
Setup script to initialize the news application with test data.

This script creates sample users, publishers, and articles for testing.
Run with: python manage.py shell < setup_data.py
"""

import os
import sys

import django
from django.apps import apps

# Add your project directory to the path
sys.path.append(
    r"C:\Users\Tsatsi\Documents\Hyperion Dev\M06\News application\news_project"
)

# Set the Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "news_project.settings")

# Setup Django
django.setup()

# NOW import Django models (move your existing imports below this line)

# Dynamically resolve models to avoid static analysis import errors
# and ensure models are resolved at runtime within Django's context.
Article = apps.get_model("news_app", "Article")
CustomUser = apps.get_model("news_app", "CustomUser")
Newsletter = apps.get_model("news_app", "Newsletter")
Publisher = apps.get_model("news_app", "Publisher")


def create_test_users():
    """Create test users for each role."""
    print("Creating test users...")

    # Create Reader
    reader, created = CustomUser.objects.get_or_create(
        username="reader1",
        defaults={
            "email": "reader@test.com",
            "role": "reader",
            "first_name": "John",
            "last_name": "Reader",
        },
    )
    if created:
        reader.set_password("testpass123")
        reader.save()
        print(f"✓ Created reader: {reader.username}")

    # Create Editor
    editor, created = CustomUser.objects.get_or_create(
        username="editor1",
        defaults={
            "email": "editor@test.com",
            "role": "editor",
            "first_name": "Jane",
            "last_name": "Editor",
        },
    )
    if created:
        editor.set_password("testpass123")
        editor.save()
        print(f"✓ Created editor: {editor.username}")

    # Create Journalists
    journalist1, created = CustomUser.objects.get_or_create(
        username="journalist1",
        defaults={
            "email": "journalist1@test.com",
            "role": "journalist",
            "first_name": "Alice",
            "last_name": "Reporter",
        },
    )
    if created:
        journalist1.set_password("testpass123")
        journalist1.save()
        print(f"✓ Created journalist: {journalist1.username}")

    journalist2, created = CustomUser.objects.get_or_create(
        username="journalist2",
        defaults={
            "email": "journalist2@test.com",
            "role": "journalist",
            "first_name": "Bob",
            "last_name": "Writer",
        },
    )
    if created:
        journalist2.set_password("testpass123")
        journalist2.save()
        print(f"✓ Created journalist: {journalist2.username}")

    return reader, editor, journalist1, journalist2


def create_publishers():
    """Create test publishers."""
    print("\nCreating publishers...")

    publisher1, created = Publisher.objects.get_or_create(
        name="Tech News Daily",
        defaults={
            "description": "Your source for technology news",
            "website": "https://technewsdaily.com",
        },
    )
    if created:
        print(f"✓ Created publisher: {publisher1.name}")

    publisher2, created = Publisher.objects.get_or_create(
        name="Global Times",
        defaults={
            "description": "International news and analysis",
            "website": "https://globaltimes.com",
        },
    )
    if created:
        print(f"✓ Created publisher: {publisher2.name}")

    return publisher1, publisher2


def create_articles(editor, journalist1, journalist2, publisher1, publisher2):
    """Create sample articles."""
    print("\nCreating articles...")

    # Approved articles
    article1, created = Article.objects.get_or_create(
        title="Introduction to Django REST Framework",
        defaults={
            "content": """Django REST Framework is a powerful toolkit for
            building Web APIs. In this article, we'll explore its core
            features and best practices.

            Key Features:
            - Serialization
            - Authentication
            - ViewSets and Routers
            - Comprehensive testing support

            Stay tuned for more in-depth tutorials!""",
            "summary": "Learn the basics of Django REST Framework",
            "author": journalist1,
            "publisher": publisher1,
            "is_approved": True,
            "approved_by": editor,
        },
    )
    if created:
        print(f"✓ Created article: {article1.title}")

    article2, created = Article.objects.get_or_create(
        title="The Future of Web Development",
        defaults={
            "content": """Web development continues to evolve at a rapid
            pace. From serverless architectures to progressive web apps,
            the landscape is constantly changing.

            Trends to Watch:
            - Edge computing
            - WebAssembly
            - AI-powered development tools
            - Low-code platforms

            The future looks exciting!""",
            "summary": "Exploring upcoming trends in web development",
            "author": journalist2,
            "publisher": publisher2,
            "is_approved": True,
            "approved_by": editor,
        },
    )
    if created:
        print(f"✓ Created article: {article2.title}")

    # Pending article
    article3, created = Article.objects.get_or_create(
        title="Database Optimization Techniques",
        defaults={
            "content": """Optimizing database queries is crucial for
            application performance. This article covers various techniques
            to improve query efficiency.

            Techniques Covered:
            - Index optimization
            - Query analysis
            - Caching strategies
            - Connection pooling

            Implementation examples included!""",
            "summary": "Master database optimization for better performance",
            "author": journalist1,
            "publisher": publisher1,
            "is_approved": False,
        },
    )
    if created:
        print(f"✓ Created pending article: {article3.title}")


def create_subscriptions(reader, journalist1, publisher1):
    """Set up subscriptions."""
    print("\nSetting up subscriptions...")

    reader.subscribed_publishers.add(publisher1)
    reader.subscribed_journalists.add(journalist1)
    reader.save()

    print("✓ Reader subscribed to Tech News Daily")
    print("✓ Reader subscribed to journalist1")


def create_newsletters(journalist1, journalist2, publisher1):
    """Create sample newsletters."""
    print("\nCreating newsletters...")

    newsletter1, created = Newsletter.objects.get_or_create(
        title="Weekly Tech Roundup - Week 1",
        defaults={
            "content": """Welcome to our weekly tech roundup!

            This Week's Highlights:
            - New framework releases
            - Industry conferences
            - Open source updates
            - Community news

            Thanks for reading!""",
            "author": journalist1,
            "publisher": publisher1,
        },
    )
    if created:
        print(f"✓ Created newsletter: {newsletter1.title}")

    newsletter2, created = Newsletter.objects.get_or_create(
        title="Independent Newsletter - Django Tips",
        defaults={
            "content": """Quick Django tips for developers:

            1. Use select_related for foreign keys
            2. Leverage prefetch_related for many-to-many
            3. Enable database query logging in development
            4. Use Django Debug Toolbar
            5. Write comprehensive tests

            Happy coding!""",
            "author": journalist2,
            "publisher": None,
        },
    )
    if created:
        print(f"✓ Created newsletter: {newsletter2.title}")


def main():
    """Main setup function."""
    print("=" * 60)
    print("News Application - Data Setup")
    print("=" * 60)

    try:
        # Create users
        reader, editor, journalist1, journalist2 = create_test_users()

        # Create publishers
        publisher1, publisher2 = create_publishers()

        # Create articles
        create_articles(editor, journalist1, journalist2, publisher1, publisher2)

        # Set up subscriptions
        create_subscriptions(reader, journalist1, publisher1)

        # Create newsletters
        create_newsletters(journalist1, journalist2, publisher1)

        print("\n" + "=" * 60)
        print("Setup completed successfully!")
        print("=" * 60)
        print("\nTest User Credentials:")
        print("-" * 60)
        print("Reader:     username=reader1,     password=testpass123")
        print("Editor:     username=editor1,     password=testpass123")
        print("Journalist: username=journalist1, password=testpass123")
        print("Journalist: username=journalist2, password=testpass123")
        print("-" * 60)

    except Exception as e:
        print(f"\n✗ Error during setup: {str(e)}")
        raise


if __name__ == "__main__":
    main()
