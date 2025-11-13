"""
Utility for posting updates to Twitter using OAuth 1.0a via Authlib.
"""

from authlib.integrations.requests_client import OAuth1Session
from django.conf import settings


def post_to_twitter(message: str):
    """Post a status update to Twitter/X using OAuth 1.0a."""
    if not getattr(settings, "ENABLE_TWITTER", False):
        return

    try:
        oauth = OAuth1Session(
            client_key=settings.TWITTER_API_KEY,
            client_secret=settings.TWITTER_API_SECRET,
            resource_owner_key=settings.TWITTER_ACCESS_TOKEN,
            resource_owner_secret=settings.TWITTER_ACCESS_TOKEN_SECRET,
        )

        # Twitter API v2 endpoint
        url = "https://api.twitter.com/2/tweets"
        payload = {"text": message}

        response = oauth.post(url, json=payload)
        response.raise_for_status()
        print(f"✅ Tweet posted successfully: {message}")

    except Exception as e:
        print(f"⚠️ Twitter post failed: {e}")
