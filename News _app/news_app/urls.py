"""
URL configuration for news_app.

This module defines all URL patterns for both web views and API endpoints.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

# Create a router for API viewsets
router = DefaultRouter()
router.register(r"articles", views.ArticleViewSet, basename="api-article")
router.register(r"newsletters", views.NewsletterViewSet, basename="api-newsletter")
router.register(r"publishers", views.PublisherViewSet, basename="api-publisher")

# Web interface URL patterns
urlpatterns = [
    # Home and dashboard
    path("", views.home, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),

    # Authentication
    path("register/", views.register, name="register"),
    path("login/", views.user_login, name="login"),
    path("logout/", views.user_logout, name="logout"),

    # Article management for journalists
    path("articles/create/", views.create_article, name="create_article"),
    path("articles/my-articles/", views.my_articles, name="my_articles"),
    path("articles/<int:pk>/edit/", views.edit_article, name="edit_article"),
    path("articles/<int:pk>/delete/", views.delete_article, name="delete_article"),
    
    # Article viewing (public/reader)
    path("articles/", views.ArticleListView.as_view(), name="article_list"),
    path(
        "articles/<int:pk>/", views.ArticleDetailView.as_view(), name="article_detail"
    ),
    # Editor views
    path("pending/", views.PendingArticlesView.as_view(), name="pending_articles"),
    path("approve/<int:pk>/", views.approve_article, name="approve_article"),
    path("reject/<int:pk>/", views.reject_article, name="reject_article"),

    # Subscribe/Unsubscribe (Web)
    path("subscriptions/", views.subscription_dashboard, name="subscription_dashboard"),
    path(
        "newsletter/<int:newsletter_id>/subscribe/",
        views.subscribe_newsletter,
        name="subscribe_newsletter",
    ),
    path(
        "newsletter/<int:newsletter_id>/unsubscribe/",
        views.unsubscribe_newsletter,
        name="unsubscribe_newsletter",
    ),
    path(
    "journalists/<int:journalist_id>/web-subscribe/",
    views.web_subscribe_to_journalist,
    name="web_subscribe_journalist",
    ),
    path(
        "journalists/<int:journalist_id>/web-unsubscribe/",
        views.web_unsubscribe_from_journalist,
        name="web_unsubscribe_journalist",
    ),

    # Newsletter URLs
    path("newsletters/", views.NewsletterListView.as_view(), name="newsletter_list"),
    path(
        "newsletters/<int:pk>/",
        views.NewsletterDetailView.as_view(),
        name="newsletter_detail",
    ),
    path("newsletters/create/", views.create_newsletter, name="create_newsletter"),
    path("newsletters/<int:pk>/edit/", views.edit_newsletter, name="edit_newsletter"),
    path(
        "newsletters/<int:pk>/delete/",
        views.delete_newsletter,
        name="delete_newsletter",
    ),
    path("my-newsletters/", views.my_newsletters, name="my_newsletters"),

    # Publisher URLs
    path("publishers/", views.publisher_list, name="publisher_list"),
    path("publishers/<int:pk>/", views.publisher_detail, name="publisher_detail"),
    path("publishers/create/", views.create_publisher, name="create_publisher"),
    path(
        "publishers/<int:pk>/dashboard/",
        views.publisher_dashboard,
        name="publisher_dashboard",
    ),
    path(
        "publishers/<int:pk>/request-join/",
        views.request_join_publisher,
        name="request_join_publisher",
    ),
    path(
        "publisher/requests/",
        views.publisher_join_requests,
        name="publisher_join_requests",
    ),
    path(
        "publishers/join-request/<int:request_id>/approve/",
        views.approve_join_request,
        name="approve_join_request",
    ),
    path(
        "publishers/join-request/<int:request_id>/reject/",
        views.reject_join_request,
        name="reject_join_request",
    ),
    path(
        "articles/<int:pk>/publish-independently/",
        views.publish_independently,
        name="publish_independently",
    ),

    # Journalist URLs 
    path("journalists/", views.journalist_list, name="journalist_list"),
    path(
        "journalists/<int:journalist_id>/subscribe/",
        views.subscribe_to_journalist,
        name="subscribe_journalist",
    ),
    path(
        "journalists/<int:journalist_id>/unsubscribe/",
        views.unsubscribe_from_journalist,
        name="unsubscribe_journalist",
    ),

    # API endpoints
    path("api/", include(router.urls)),
    path(
        "api/journalists/<int:journalist_id>/articles/",
        views.JournalistArticlesView.as_view(),
        name="journalist-articles",
    ),
    path(
        "api/subscriptions/articles/",
        views.SubscriptionArticlesView.as_view(),
        name="subscription-articles",
    ),
    path(
        "api/subscriptions/publishers/<int:publisher_id>/subscribe/",
        views.subscribe_to_publisher,
        name="subscribe-publisher",
    ),
    path(
        "api/subscriptions/publishers/<int:publisher_id>/unsubscribe/",
        views.unsubscribe_from_publisher,
        name="unsubscribe-publisher",
    ),
    path(
        "api/subscriptions/journalists/<int:journalist_id>/subscribe/",
        views.subscribe_to_journalist,
        name="subscribe-journalist",
    ),
    path(
        "api/subscriptions/journalists/<int:journalist_id>/unsubscribe/",
        views.unsubscribe_from_journalist,
        name="unsubscribe-journalist",
    ),
    path(
        "api/subscriptions/my-subscriptions/",
        views.my_subscriptions,
        name="my-subscriptions",
    ),
]
