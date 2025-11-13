"""
Views for the news application.

This module contains both template-based views for the web interface
and API views for the RESTful API.
"""

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.generic import DetailView, ListView
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .forms import ArticleForm, NewsletterForm, PublisherForm, UserRegistrationForm
from .models import Article, CustomUser, Newsletter, Publisher, PublisherJoinRequest
from .permissions import IsEditor, IsJournalist
from .serializers import (
    ArticleCreateSerializer,
    ArticleSerializer,
    NewsletterCreateSerializer,
    NewsletterSerializer,
    PublisherSerializer,
    SubscriptionArticleSerializer,
)


def register(request):
    """
    Handle user registration.

    Args:
        request: HTTP request object.

    Returns:
        HttpResponse: Rendered registration form or redirect.
    """
    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get("username")
            role = form.cleaned_data.get("role")
            messages.success(request, f"Account created for {username} as {role}!")
            login(request, user)
            return redirect("home")
        else:
            messages.error(
                request, "Registration failed. Please check the details and try again."
            )
    else:
        form = UserRegistrationForm()

    return render(request, "news_app/register.html", {"form": form})


def user_login(request):
    """
    Handle user login.

    Args:
        request: HTTP request object.

    Returns:
        HttpResponse: Rendered login form or redirect.
    """
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {username}!")
                return redirect("home")
    else:
        form = AuthenticationForm()

    return render(request, "news_app/login.html", {"form": form})


def user_logout(request):
    """
    Handle user logout.

    Args:
        request: HTTP request object.

    Returns:
        HttpResponse: Redirect to home page.
    """
    logout(request)
    messages.success(request, "You have been logged out successfully!")
    return redirect("home")


def home(request):
    """
    Display home page with list of approved articles.

    Shows the latest approved articles for all visitors.

    Args:
        request: HTTP request object.

    Returns:
        HttpResponse: Rendered home page with articles.
    """
    # Get latest approved articles
    articles = (
        Article.objects.filter(is_approved=True)
        .select_related("author", "publisher")
        .order_by("-published_date")[:10]
    )

    context = {
        "articles": articles,
        "total_articles": Article.objects.filter(is_approved=True).count(),
    }

    return render(request, "news_app/home.html", context)


# Article creation and management views for journalists


@login_required
def create_article(request):
    """
    Allow journalists to create new articles.

    Journalists can create articles independently or through a publisher.
    Only users with 'journalist' role can access this view.

    Args:
        request: HTTP request object.

    Returns:
        HttpResponse: Rendered form or redirect after creation.
    """
    if request.user.role != "journalist":
        messages.error(request, "Only journalists can create articles.")
        return redirect("home")

    if request.method == "POST":
        form = ArticleForm(
            request.POST, request.FILES, user=request.user
        )  # ← Add user=request.user
        if form.is_valid():
            article = form.save(commit=False)
            article.author = request.user
            article.save()
            messages.success(
                request, "Article created successfully! It is pending editor approval."
            )
            return redirect("my_articles")
    else:
        form = ArticleForm(user=request.user)  # ← Add user=request.user

    context = {"form": form, "title": "Create New Article"}
    return render(request, "news_app/article_form.html", context)


@login_required
def edit_article(request, pk):
    """
    Allow journalists to edit their own articles.

    Journalists can only edit articles they authored and that
    haven't been approved yet.

    Args:
        request: HTTP request object.
        pk: Primary key of the article to edit.

    Returns:
        HttpResponse: Rendered form or redirect after editing.
    """
    article = get_object_or_404(Article, pk=pk)

    if article.author != request.user:
        messages.error(request, "You can only edit your own articles.")
        return redirect("my_articles")

    if article.is_approved:
        messages.error(
            request, "Cannot edit approved articles. Please contact an editor."
        )
        return redirect("my_articles")

    if request.method == "POST":
        form = ArticleForm(
            request.POST, request.FILES, instance=article, user=request.user
        )  # ← Add user
        if form.is_valid():
            form.save()
            messages.success(request, "Article updated successfully!")
            return redirect("my_articles")
    else:
        form = ArticleForm(instance=article, user=request.user)  # ← Add user

    context = {"form": form, "article": article, "title": "Edit Article"}
    return render(request, "news_app/article_form.html", context)


@login_required
def delete_article(request, pk):
    """
    Allow journalists to delete their own unapproved articles.

    Args:
        request: HTTP request object.
        pk: Primary key of the article to delete.

    Returns:
        HttpResponse: Confirmation page or redirect after deletion.
    """
    article = get_object_or_404(Article, pk=pk)

    # Check if user is the author
    if article.author != request.user:
        messages.error(request, "You can only delete your own articles.")
        return redirect("my_articles")

    # Check if article is already approved
    if article.is_approved:
        messages.error(
            request, "Cannot delete approved articles. Please contact an editor."
        )
        return redirect("my_articles")

    if request.method == "POST":
        article.delete()
        messages.success(request, "Article deleted successfully!")
        return redirect("my_articles")

    context = {"article": article}
    return render(request, "news_app/article_confirm_delete.html", context)


@login_required
def my_articles(request):
    """
    Display list of articles created by the logged-in journalist.

    Only accessible to journalists. Shows both approved and pending articles.

    Args:
        request: HTTP request object.

    Returns:
        HttpResponse: Rendered list of journalist's articles.
    """
    if request.user.role != "journalist":
        messages.error(request, "Only journalists can access this page.")
        return redirect("home")

    articles = (
        Article.objects.filter(author=request.user)
        .select_related("publisher", "approved_by")
        .order_by("-created_at")
    )

    context = {
        "articles": articles,
        "pending_count": articles.filter(is_approved=False).count(),
        "approved_count": articles.filter(is_approved=True).count(),
    }
    return render(request, "news_app/my_articles.html", context)


# Newsletter creation and management


@login_required
def create_newsletter(request):
    """Allow journalists to create new newsletters."""
    if request.user.role != "journalist":
        messages.error(request, "Only journalists can create newsletters.")
        return redirect("home")

    if request.method == "POST":
        form = NewsletterForm(
            request.POST, user=request.user
        )  # ← Add user=request.user
        if form.is_valid():
            newsletter = form.save(commit=False)
            newsletter.author = request.user
            newsletter.save()
            messages.success(request, "Newsletter created successfully!")
            return redirect("my_newsletters")
    else:
        form = NewsletterForm(user=request.user)  # ← Add user=request.user

    context = {"form": form, "title": "Create New Newsletter"}
    return render(request, "news_app/newsletter_form.html", context)


@login_required
def edit_newsletter(request, pk):
    """Allow journalists to edit their own newsletters."""
    newsletter = get_object_or_404(Newsletter, pk=pk)

    if newsletter.author != request.user:
        messages.error(request, "You can only edit your own newsletters.")
        return redirect("my_newsletters")

    if request.method == "POST":
        form = NewsletterForm(
            request.POST, instance=newsletter, user=request.user
        )  # ← Add user
        if form.is_valid():
            form.save()
            messages.success(request, "Newsletter updated successfully!")
            return redirect("my_newsletters")
    else:
        form = NewsletterForm(instance=newsletter, user=request.user)  # ← Add user

    context = {"form": form, "newsletter": newsletter, "title": "Edit Newsletter"}
    return render(request, "news_app/newsletter_form.html", context)


@login_required
def delete_newsletter(request, pk):
    """
    Allow journalists to delete their own newsletters.
    """
    newsletter = get_object_or_404(Newsletter, pk=pk)

    if newsletter.author != request.user:
        messages.error(request, "You can only delete your own newsletters.")
        return redirect("my_newsletters")

    if request.method == "POST":
        newsletter.delete()
        messages.success(request, "Newsletter deleted successfully!")
        return redirect("my_newsletters")

    context = {"newsletter": newsletter}
    return render(request, "news_app/newsletter_confirm_delete.html", context)


@login_required
def my_newsletters(request):
    """
    Display list of newsletters created by the logged-in journalist.
    """
    if request.user.role != "journalist":
        messages.error(request, "Only journalists can access this page.")
        return redirect("home")

    newsletters = (
        Newsletter.objects.filter(author=request.user)
        .select_related("publisher")
        .order_by("-created_at")
    )

    context = {
        "newsletters": newsletters,
        "total_count": newsletters.count(),
    }
    return render(request, "news_app/my_newsletters.html", context)


class NewsletterListView(ListView):
    """Display list of all newsletters."""

    model = Newsletter
    template_name = "news_app/newsletter_list.html"
    context_object_name = "newsletters"
    paginate_by = 10

    def get_queryset(self):
        return (
            Newsletter.objects.all()
            .select_related("author", "publisher")
            .order_by("-published_date")
        )


class NewsletterDetailView(DetailView):
    """Display detailed view of a single newsletter."""

    model = Newsletter
    template_name = "news_app/newsletter_detail.html"
    context_object_name = "newsletter"

    def get_context_data(self, **kwargs):
        """Add related newsletters to context."""
        context = super().get_context_data(**kwargs)

        # Get other newsletters by the same author (exclude current one)
        context["related_newsletters"] = (
            Newsletter.objects.filter(author=self.object.author)
            .exclude(pk=self.object.pk)
            .order_by("-published_date")[:5]
        )

        return context


# Template-based views for web interface


class ArticleListView(ListView):
    """
    Display list of approved articles.

    Shows only approved articles to all users.
    """

    model = Article
    template_name = "news_app/article_list.html"
    context_object_name = "articles"
    paginate_by = 10

    def get_queryset(self):
        """
        Return only approved articles.

        Returns:
            QuerySet: Filtered queryset of approved articles.
        """
        return (
            Article.objects.filter(is_approved=True)
            .select_related("author", "publisher")
            .order_by("-published_date")
        )


class ArticleDetailView(DetailView):
    """
    Display detailed view of a single article.

    Shows article details to all users if approved, or to the author
    and editors if not yet approved.
    """

    model = Article
    template_name = "news_app/article_detail.html"
    context_object_name = "article"

    def get_queryset(self):
        """
        Return articles based on user permissions.

        Returns:
            QuerySet: Filtered queryset based on user role.
        """
        user = self.request.user

        if not user.is_authenticated:
            return Article.objects.filter(is_approved=True)

        if user.role == "editor":
            return Article.objects.all()
        elif user.role == "journalist":
            return Article.objects.filter(Q(is_approved=True) | Q(author=user))
        else:
            return Article.objects.filter(is_approved=True)


class PendingArticlesView(LoginRequiredMixin, ListView):
    """
    Display list of articles pending approval.

    Only accessible to users with Editor role.
    """

    model = Article
    template_name = "news_app/pending_articles.html"
    context_object_name = "articles"

    def dispatch(self, request, *args, **kwargs):
        """
        Check if user has editor role before allowing access.

        Args:
            request: The HTTP request.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            HttpResponse: Response or redirect.
        """
        if not request.user.is_authenticated:
            return redirect("login")
        if request.user.role != "editor":
            return redirect("article_list")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        """
        Return only unapproved articles.

        Returns:
            QuerySet: Articles that haven't been approved yet.
        """
        return (
            Article.objects.filter(is_approved=False)
            .select_related("author", "publisher")
            .order_by("-created_at")
        )


@login_required
@permission_required("news_app.approve_article", raise_exception=True)
def approve_article(request, pk):
    """
    Approve an article for publication.

    This view allows editors to approve articles. Upon approval,
    signals are triggered to notify subscribers.

    Args:
        request: The HTTP request.
        pk: Primary key of the article to approve.

    Returns:
        HttpResponse: Rendered template or redirect.
    """
    article = get_object_or_404(Article, pk=pk)

    if request.method == "POST":
        article.is_approved = True
        article.approved_by = request.user
        article.approval_date = timezone.now()
        article.published_date = timezone.now()
        article.save()
        return redirect("pending_articles")

    context = {"article": article}
    return render(request, "news_app/approve_article.html", context)


@login_required
def dashboard(request):
    """
    Display role-specific dashboard.

    Shows different information based on user role:
    - Readers: Subscriptions and latest articles
    - Editors: Pending approvals and statistics
    - Journalists: Own articles and submission stats

    Args:
        request: The HTTP request.

    Returns:
        HttpResponse: Rendered dashboard template.
    """

    user = request.user
    context = {"user": user}

    if user.role == "reader":
        context["subscribed_publishers"] = user.subscribed_publishers.all()
        context["subscribed_journalists"] = user.subscribed_journalists.all()
        context["latest_articles"] = Article.objects.filter(is_approved=True).order_by(
            "-published_date"
        )[:5]

    elif user.role == "editor":
        context["pending_count"] = Article.objects.filter(is_approved=False).count()
        context["approved_count"] = Article.objects.filter(
            is_approved=True, approved_by=user
        ).count()
        context["recent_pending"] = Article.objects.filter(is_approved=False).order_by(
            "-created_at"
        )[:5]

    elif user.role == "journalist":
        context["my_articles"] = user.independent_articles.all()[:5]
        context["approved_articles"] = user.independent_articles.filter(
            is_approved=True
        ).count()
        context["pending_articles"] = user.independent_articles.filter(
            is_approved=False
        ).count()
        # ADD THIS LINE:
        context["total_newsletters"] = user.independent_newsletters.count()

    return render(request, "news_app/dashboard.html", context)


# Publisher registration


@login_required
def create_publisher(request):
    """
    Allow users with 'publisher' role to create a Publisher organization.

    This should be called after a user registers with role='publisher'.
    """
    if request.user.role != "publisher":
        messages.error(request, "Only users with publisher role can create publishers.")
        return redirect("home")

    # Check if user already has a publisher
    existing_publisher = Publisher.objects.filter(
        Q(editors=request.user) | Q(journalists=request.user)
    ).first()

    if existing_publisher:
        messages.info(
            request, f"You are already associated with {existing_publisher.name}"
        )
        return redirect("publisher_dashboard", pk=existing_publisher.pk)

    if request.method == "POST":
        form = PublisherForm(request.POST)
        if form.is_valid():
            publisher = form.save()
            # Automatically add the creator as an editor
            publisher.editors.add(request.user)
            message = (
                f'Publisher "{publisher.name}" created successfully! '
                "You have been added as an editor."
            )
            messages.success(request, message)
            return redirect("publisher_dashboard", pk=publisher.pk)
    else:
        form = PublisherForm()

    context = {"form": form, "title": "Create Publisher"}
    return render(request, "news_app/publisher_form.html", context)


def publisher_list(request):
    """
    Display list of ALL publishers.

    Shows all publishers in the database, including those added via Django admin.
    Available to all users (authenticated and anonymous).

    Args:
        request: HTTP request object.

    Returns:
        HttpResponse: Rendered publisher list page.
    """
    # Get ALL publishers - no filtering
    publishers = Publisher.objects.all().order_by("name")

    context = {
        "publishers": publishers,
        "total_count": publishers.count(),
    }

    return render(request, "news_app/publisher_list.html", context)


def publisher_detail(request, pk):
    """
    Display detailed view of a single publisher.

    Shows publisher information, editors, journalists, and recent articles.
    Available to all users.

    Args:
        request: HTTP request object.
        pk: Primary key of the publisher.

    Returns:
        HttpResponse: Rendered publisher detail page.
    """
    publisher = get_object_or_404(Publisher, pk=pk)

    # Get recent approved articles from this publisher
    recent_articles = (
        Article.objects.filter(publisher=publisher, is_approved=True)
        .select_related("author")
        .order_by("-published_date")[:10]
    )

    # Check if current user is a member (if authenticated)
    is_member = False
    can_request_join = False

    if request.user.is_authenticated:
        if request.user.role == "journalist":
            is_member = publisher.journalists.filter(pk=request.user.pk).exists()
            can_request_join = not is_member
        elif request.user.role == "editor":
            is_member = publisher.editors.filter(pk=request.user.pk).exists()
            can_request_join = not is_member

    context = {
        "publisher": publisher,
        "recent_articles": recent_articles,
        "editors": publisher.editors.all(),
        "journalists": publisher.journalists.all(),
        "is_member": is_member,
        "can_request_join": can_request_join,
    }

    return render(request, "news_app/publisher_detail.html", context)


# Publisher request


@login_required
def request_join_publisher(request, publisher_id):
    """
    Allow journalists/editors to request to join a publisher.
    """
    if request.user.role not in ["journalist", "editor"]:
        messages.error(request, "Only journalists and editors can join publishers.")
        return redirect("publisher_list")

    publisher = get_object_or_404(Publisher, pk=publisher_id)

    # Check if already a member
    if request.user.role == "journalist":
        if publisher.journalists.filter(pk=request.user.pk).exists():
            messages.info(request, f"You are already a member of {publisher.name}")
            return redirect("publisher_detail", pk=publisher_id)
    elif request.user.role == "editor":
        if publisher.editors.filter(pk=request.user.pk).exists():
            messages.info(request, f"You are already a member of {publisher.name}")
            return redirect("publisher_detail", pk=publisher_id)

    # Check for existing pending request
    existing_request = PublisherJoinRequest.objects.filter(
        user=request.user, publisher=publisher, status="pending"
    ).first()

    if existing_request:
        messages.info(request, "You already have a pending request for this publisher.")
        return redirect("publisher_detail", pk=publisher_id)

    if request.method == "POST":
        message = request.POST.get("message", "")
        PublisherJoinRequest.objects.create(
            user=request.user, publisher=publisher, message=message
        )
        messages.success(
            request, f"Your request to join {publisher.name} has been submitted!"
        )
        return redirect("publisher_detail", pk=publisher_id)

    context = {"publisher": publisher}
    return render(request, "news_app/request_join_publisher.html", context)


@login_required
def publisher_dashboard(request, pk):
    """
    Display publisher dashboard for editors.

    Shows join requests, articles, and publisher info.
    """
    publisher = get_object_or_404(Publisher, pk=pk)

    # Check if user is an editor of this publisher
    if not publisher.editors.filter(pk=request.user.pk).exists():
        messages.error(
            request, "You do not have permission to access this publisher dashboard."
        )
        return redirect("publisher_detail", pk=pk)

    pending_requests = PublisherJoinRequest.objects.filter(
        publisher=publisher, status="pending"
    ).select_related("user")

    context = {
        "publisher": publisher,
        "pending_requests": pending_requests,
        "editors": publisher.editors.all(),
        "journalists": publisher.journalists.all(),
        "articles": publisher.articles.all()[:10],
    }
    return render(request, "news_app/publisher_dashboard.html", context)


@login_required
def approve_join_request(request, request_id):
    """
    Approve a join request to a publisher.
    """
    join_request = get_object_or_404(PublisherJoinRequest, pk=request_id)
    publisher = join_request.publisher

    # Check if user is an editor of this publisher
    if not publisher.editors.filter(pk=request.user.pk).exists():
        messages.error(request, "Only publisher editors can approve join requests.")
        return redirect("home")

    if join_request.status != "pending":
        messages.warning(request, "This request has already been reviewed.")
        return redirect("publisher_dashboard", pk=publisher.pk)

    join_request.status = "approved"
    join_request.reviewed_by = request.user
    join_request.reviewed_at = timezone.now()
    join_request.save()

    # Add user to appropriate group
    if join_request.user.role == "journalist":
        publisher.journalists.add(join_request.user)
    elif join_request.user.role == "editor":
        publisher.editors.add(join_request.user)

    messages.success(
        request, f"{join_request.user.username} has been added to {publisher.name}!"
    )
    return redirect("publisher_dashboard", pk=publisher.pk)


@login_required
def reject_join_request(request, request_id):
    """
    Reject a join request to a publisher.
    """
    join_request = get_object_or_404(PublisherJoinRequest, pk=request_id)
    publisher = join_request.publisher

    # Check if user is an editor of this publisher
    if not publisher.editors.filter(pk=request.user.pk).exists():
        messages.error(request, "Only publisher editors can reject join requests.")
        return redirect("home")

    if join_request.status != "pending":
        messages.warning(request, "This request has already been reviewed.")
        return redirect("publisher_dashboard", pk=publisher.pk)

    join_request.status = "rejected"
    join_request.reviewed_by = request.user
    join_request.reviewed_at = timezone.now()
    join_request.save()

    messages.success(request, "Join request has been rejected.")
    return redirect("publisher_dashboard", pk=publisher.pk)


@login_required
def web_subscribe_to_publisher(request, publisher_id):
    """Web interface to subscribe to a publisher."""
    if request.user.role != "reader":
        messages.error(request, "Only readers can subscribe to publishers.")
        return redirect("publisher_detail", pk=publisher_id)

    publisher = get_object_or_404(Publisher, id=publisher_id)

    if publisher in request.user.subscribed_publishers.all():
        messages.info(request, f"You are already subscribed to {publisher.name}.")
    else:
        request.user.subscribed_publishers.add(publisher)
        messages.success(request, f"Successfully subscribed to {publisher.name}!")

    return redirect("publisher_detail", pk=publisher_id)


@login_required
def web_unsubscribe_from_publisher(request, publisher_id):
    """Web interface to unsubscribe from a publisher."""
    if request.user.role != "reader":
        messages.error(request, "Only readers can manage subscriptions.")
        return redirect("publisher_detail", pk=publisher_id)

    publisher = get_object_or_404(Publisher, id=publisher_id)

    if publisher not in request.user.subscribed_publishers.all():
        messages.info(request, f"You are not subscribed to {publisher.name}.")
    else:
        request.user.subscribed_publishers.remove(publisher)
        messages.success(request, f"Successfully unsubscribed from {publisher.name}.")

    return redirect("publisher_detail", pk=publisher_id)


@login_required
def subscription_dashboard(request):
    """Display user's subscriptions dashboard."""
    if request.user.role != "reader":
        messages.error(request, "Only readers have subscriptions.")
        return redirect("home")

    context = {
        "subscribed_publishers": request.user.subscribed_publishers.all(),
        "subscribed_journalists": request.user.subscribed_journalists.all(),
    }
    return render(request, "news_app/subscription_dashboard.html", context)


# REST API Views


class ArticleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Article CRUD operations via API.

    Provides list, create, retrieve, update, and delete actions
    for articles based on user permissions.
    """

    queryset = Article.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """
        Return appropriate serializer based on action.

        Returns:
            Serializer class: ArticleCreateSerializer for create,
                             ArticleSerializer for other actions.
        """
        if self.action == "create":
            return ArticleCreateSerializer
        return ArticleSerializer

    def get_queryset(self):
        """
        Return articles based on user role.

        Returns:
            QuerySet: Filtered articles based on permissions.
        """
        user = self.request.user

        if user.role == "editor":
            return Article.objects.all()
        elif user.role == "journalist":
            return Article.objects.filter(Q(is_approved=True) | Q(author=user))
        else:
            return Article.objects.filter(is_approved=True)

    def get_permissions(self):
        """
        Set permissions based on action.

        Returns:
            list: List of permission instances.
        """
        if self.action == "create":
            return [IsJournalist()]
        elif self.action in ["update", "partial_update", "destroy"]:
            return [IsEditor()]
        return [IsAuthenticated()]


class NewsletterViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Newsletter CRUD operations via API.

    Provides list, create, retrieve, update, and delete actions
    for newsletters based on user permissions.
    """

    queryset = Newsletter.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """
        Return appropriate serializer based on action.

        Returns:
            Serializer class: Appropriate serializer for the action.
        """
        if self.action == "create":
            return NewsletterCreateSerializer
        return NewsletterSerializer

    def get_permissions(self):
        """
        Set permissions based on action.

        Returns:
            list: List of permission instances.
        """
        if self.action == "create":
            return [IsJournalist()]
        elif self.action in ["update", "partial_update", "destroy"]:
            return [IsEditor()]
        return [IsAuthenticated()]


class PublisherViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Publisher read-only operations via API.

    Provides list and retrieve actions for publishers.
    """

    queryset = Publisher.objects.all()
    serializer_class = PublisherSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=["get"])
    def articles(self, request, pk=None):
        """
        Get all approved articles for a specific publisher.

        Args:
            request: The HTTP request.
            pk: Publisher primary key.

        Returns:
            Response: Paginated list of articles.
        """
        publisher = self.get_object()
        articles = Article.objects.filter(
            publisher=publisher, is_approved=True
        ).order_by("-published_date")

        page = self.paginate_queryset(articles)
        if page is not None:
            serializer = ArticleSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ArticleSerializer(articles, many=True)
        return Response(serializer.data)


class JournalistArticlesView(generics.ListAPIView):
    """
    API view to retrieve articles by a specific journalist.

    Returns only approved articles authored by the journalist.
    """

    serializer_class = ArticleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Get articles by journalist ID from URL.

        Returns:
            QuerySet: Approved articles by the journalist.
        """
        journalist_id = self.kwargs.get("journalist_id")
        return Article.objects.filter(
            author_id=journalist_id, is_approved=True
        ).order_by("-published_date")


class SubscriptionArticlesView(generics.ListAPIView):
    """
    API view for retrieving articles based on user subscriptions.

    Returns approved articles from publishers and journalists
    that the authenticated user is subscribed to.
    """

    serializer_class = SubscriptionArticleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Get articles based on user's subscriptions.

        Returns:
            QuerySet: Articles from subscribed publishers and journalists.
        """
        user = self.request.user

        if user.role != "reader":
            return Article.objects.none()

        # Get subscribed publishers and journalists
        subscribed_publishers = user.subscribed_publishers.all()
        subscribed_journalists = user.subscribed_journalists.all()

        # Query for articles from subscriptions
        articles = (
            Article.objects.filter(
                Q(publisher__in=subscribed_publishers)
                | Q(author__in=subscribed_journalists),
                is_approved=True,
            )
            .distinct()
            .order_by("-published_date")
        )

        return articles


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def subscribe_to_publisher(request, publisher_id):
    """
    Subscribe the authenticated user to a publisher.

    Only readers can subscribe.

    Args:
        request: HTTP request
        publisher_id: ID of the publisher to subscribe to

    Returns:
        Response with success/error message
    """
    if request.user.role != "reader":
        return Response(
            {"error": "Only readers can subscribe to publishers"},
            status=status.HTTP_403_FORBIDDEN,
        )

    publisher = get_object_or_404(Publisher, id=publisher_id)

    if publisher in request.user.subscribed_publishers.all():
        return Response(
            {"message": f"Already subscribed to {publisher.name}"},
            status=status.HTTP_200_OK,
        )

    request.user.subscribed_publishers.add(publisher)

    return Response(
        {
            "message": f"Successfully subscribed to {publisher.name}",
            "publisher": {"id": publisher.id, "name": publisher.name},
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def unsubscribe_from_publisher(request, publisher_id):
    """
    Unsubscribe the authenticated user from a publisher.

    Args:
        request: HTTP request
        publisher_id: ID of the publisher to unsubscribe from

    Returns:
        Response with success/error message
    """
    if request.user.role != "reader":
        return Response(
            {"error": "Only readers can manage subscriptions"},
            status=status.HTTP_403_FORBIDDEN,
        )

    publisher = get_object_or_404(Publisher, id=publisher_id)

    if publisher not in request.user.subscribed_publishers.all():
        return Response(
            {"message": f"Not subscribed to {publisher.name}"},
            status=status.HTTP_200_OK,
        )

    request.user.subscribed_publishers.remove(publisher)

    return Response(
        {"message": f"Successfully unsubscribed from {publisher.name}"},
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def subscribe_to_journalist(request, journalist_id):
    """
    Subscribe the authenticated user to a journalist.

    Only readers can subscribe.

    Args:
        request: HTTP request
        journalist_id: ID of the journalist to subscribe to

    Returns:
        Response with success/error message
    """
    if request.user.role != "reader":
        return Response(
            {"error": "Only readers can subscribe to journalists"},
            status=status.HTTP_403_FORBIDDEN,
        )

    journalist = get_object_or_404(CustomUser, id=journalist_id, role="journalist")

    if journalist in request.user.subscribed_journalists.all():
        return Response(
            {"message": f"Already subscribed to {journalist.username}"},
            status=status.HTTP_200_OK,
        )

    request.user.subscribed_journalists.add(journalist)

    return Response(
        {
            "message": f"Successfully subscribed to {journalist.username}",
            "journalist": {"id": journalist.id, "username": journalist.username},
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def unsubscribe_from_journalist(request, journalist_id):
    """
    Unsubscribe the authenticated user from a journalist.

    Args:
        request: HTTP request
        journalist_id: ID of the journalist to unsubscribe from

    Returns:
        Response with success/error message
    """
    if request.user.role != "reader":
        return Response(
            {"error": "Only readers can manage subscriptions"},
            status=status.HTTP_403_FORBIDDEN,
        )

    journalist = get_object_or_404(CustomUser, id=journalist_id, role="journalist")

    if journalist not in request.user.subscribed_journalists.all():
        return Response(
            {"message": f"Not subscribed to {journalist.username}"},
            status=status.HTTP_200_OK,
        )

    request.user.subscribed_journalists.remove(journalist)

    return Response(
        {"message": f"Successfully unsubscribed from {journalist.username}"},
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_subscriptions(request):
    """
    Get all subscriptions for the authenticated user.

    Only readers have subscriptions.

    Args:
        request: HTTP request

    Returns:
        Response with list of subscriptions
    """
    if request.user.role != "reader":
        return Response(
            {"error": "Only readers have subscriptions"},
            status=status.HTTP_403_FORBIDDEN,
        )

    publishers = request.user.subscribed_publishers.all()
    journalists = request.user.subscribed_journalists.all()

    return Response(
        {
            "publishers": [
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "website": p.website,
                }
                for p in publishers
            ],
            "journalists": [
                {
                    "id": j.id,
                    "username": j.username,
                    "email": j.email,
                    "full_name": j.get_full_name(),
                }
                for j in journalists
            ],
        }
    )
