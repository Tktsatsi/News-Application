"""
Signal handlers for the news application.

This module contains signal handlers that trigger when articles are approved,
sending email notifications to subscribers and posting to Twitter/X.
"""

from django.conf import settings
from django.core.mail import send_mass_mail
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Article
from .utilities.twitter import post_to_twitter


@receiver(pre_save, sender=Article)
def set_approval_date(sender, instance, **kwargs):
    """
    Set approval date when article is approved.

    Args:
        sender: The model class (Article).
        instance: The actual instance being saved.
        **kwargs: Additional keyword arguments.
    """
    if instance.pk:
        try:
            old_instance = Article.objects.get(pk=instance.pk)
            # If article is being approved for the first time
            if not old_instance.is_approved and instance.is_approved:
                instance.approval_date = timezone.now()
                if not instance.published_date:
                    instance.published_date = timezone.now()
        except Article.DoesNotExist:
            pass


@receiver(post_save, sender=Article)
def notify_subscribers_on_approval(sender, instance, created, **kwargs):
    """
    Send email notifications and post to Twitter when an article is approved.

    This signal handler is triggered after an Article is saved.
    If the article has just been approved, it:
    1. Sends email notifications to all subscribers
    2. Posts to Twitter/X

    Args:
        sender: The model class (Article).
        instance: The actual instance being saved.
        created: Boolean indicating if this is a new instance.
        **kwargs: Additional keyword arguments.
    """
    # Only process if article is approved
    if not instance.is_approved:
        return

    # Check if this was just approved (not created as already approved)
    if not created:
        try:
            # We need to check if this is a new approval
            # Since we're in post_save, we can't access the old state directly
            # We'll use a workaround by checking if approval_date was just set
            if instance.approval_date:
                time_since_approval = timezone.now() - instance.approval_date
                # If approved more than 10 seconds ago, skip(already processed)
                if time_since_approval.total_seconds() > 10:
                    return
        except Exception:
            pass

    # Send email notifications
    send_email_notifications(instance)

    # Post to Twitter/X
    # Build tweet text and post via utilities.twitter.post_to_twitter
    tweet_text = _build_tweet_text(instance)
    post_to_twitter(tweet_text)


def send_email_notifications(article):
    """
    Send email notifications to all subscribers.

    Collects all subscribers to the article's publisher and author,
    then sends mass email notifications about the new article.

    :param article: The Article instance that was approved
    :type article: Article

    .. note::
        The article author is excluded from the notification list.
        Uses Django's send_mass_mail for efficient bulk email sending.
    """
    # Collect all subscribers
    subscribers = set()

    # Get subscribers to the publisher
    if article.publisher:
        publisher_subscribers = article.publisher.subscribed_readers.all()
        subscribers.update(publisher_subscribers)

    # Get subscribers to the journalist/author
    journalist_subscribers = article.author.journalist_subscribers.all()
    subscribers.update(journalist_subscribers)

    # Remove the author from subscribers list
    subscribers.discard(article.author)

    if not subscribers:
        print(f"No subscribers to notify for article: {article.title}")
        return

    # Prepare email messages
    subject = f"New Article Published: {article.title}"
    message = f"""
Hello,

A new article has been published that you might be interested in:

Title: {article.title}
Author: {article.author.get_full_name() or article.author.username}
Publisher: {article.publisher.name if article.publisher else 'Independent'}

Summary:
{article.summary or article.content[:200] + '...'}

Read the full article on our website.

Best regards,
The News Team
    """

    # Create mass email list
    emails = []
    for subscriber in subscribers:
        if subscriber.email:
            email_tuple = (
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [subscriber.email],
            )
            emails.append(email_tuple)

    # Send all emails
    if emails:
        try:
            send_mass_mail(emails, fail_silently=False)
            print(
                f"✓ Sent {len(emails)} notification emails for "
                f"article: {article.title}"
            )
        except Exception as e:
            print(f"✗ Error sending notification emails: {str(e)}")


def _build_tweet_text(article):
    """
    Build a concise tweet text for an Article instance.

    Creates a tweet with article title and summary/content excerpt,
    ensuring the total length does not exceed 280 characters.

    :param article: The Article instance to build tweet text for
    :type article: Article
    :returns: Tweet text (max 280 characters) with article title and content
    :rtype: str
    """
    tweet_text = f"New Article: {article.title}\n\n"

    if article.summary:
        # Add summary if it fits
        remaining_chars = 280 - len(tweet_text) - 3  # -3 for "..."
        if len(article.summary) <= remaining_chars:
            tweet_text += article.summary
        else:
            tweet_text += article.summary[:remaining_chars] + "..."
    else:
        # Use content excerpt
        remaining_chars = 280 - len(tweet_text) - 3
        content_excerpt = (article.content or "")[:remaining_chars] + "..."
        tweet_text += content_excerpt

    return tweet_text
