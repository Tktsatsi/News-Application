"""
Views for the news application.

This module contains template-based views for the web interface
and API views for the RESTful API.
"""

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
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

from .forms import (
    ArticleForm,
    NewsletterForm,
    PublisherForm,
    UserRegistrationForm,
)
from .models import (
    Article,
    CustomUser,
    Newsletter,
    Publisher,
    PublisherJoinRequest,
)
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

    :param request: HTTP request object
    :type request: HttpRequest
    :returns: Rendered registration page or redirect on success
    :rtype: HttpResponse
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
        messages.error(
            request, "Registration failed. Please check the details and try again."
        )
    else:
        form = UserRegistrationForm()

    return render(request, "news_app/register.html", {"form": form})


def user_login(request):
    """
    Handle user login.

    :param request: HTTP request object
    :type request: HttpRequest
    :returns: Rendered login page or redirect on success
    :rtype: HttpResponse
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

    :param request: HTTP request object
    :type request: HttpRequest
    :returns: Redirect to home page
    :rtype: HttpResponse
    """
    logout(request)
    messages.success(request, "You have been logged out successfully!")
    return redirect("home")


def home(request):
    """
    Display home page with latest approved articles.

    :param request: HTTP request object
    :type request: HttpRequest
    :returns: Rendered home page with articles
    :rtype: HttpResponse
    """
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


@login_required
def create_article(request):
    """
    Allow journalists to create new articles.

    :param request: HTTP request object
    :type request: HttpRequest
    :returns: Rendered form or redirect after creation
    :rtype: HttpResponse
    """
    if request.user.role != "journalist":
        messages.error(request, "Only journalists can create articles.")
        return redirect("home")

    if request.method == "POST":
        form = ArticleForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            article = form.save(commit=False)
            article.author = request.user
            article.save()
            messages.success(
                request,
                "Article created successfully! It is pending editor approval.",
            )
            return redirect("my_articles")
    else:
        form = ArticleForm(user=request.user)

    return render(
        request, "news_app/article_form.html", {"form": form, "title": "Create New Article"}
    )


@login_required
def edit_article(request, pk):
    """
    Journalists can edit their own unapproved articles. Editors can edit any.

    :param request: HTTP request object
    :type request: HttpRequest
    :param pk: Primary key of the article
    :type pk: int
    :returns: Rendered edit form or redirect after saving
    :rtype: HttpResponse
    """
    article = get_object_or_404(Article, pk=pk)
    user = request.user

    if user.role == "journalist":
        if article.author != user:
            messages.error(request, "You can only edit your own articles.")
            return redirect("my_articles")
        if article.is_approved:
            messages.error(request, "Cannot edit approved articles. Contact an editor.")
            return redirect("my_articles")
    elif user.role != "editor":
        messages.error(request, "You do not have permission to edit articles.")
        return redirect("home")

    if request.method == "POST":
        form = ArticleForm(request.POST, request.FILES, instance=article, user=user)
        if form.is_valid():
            article_instance = form.save(commit=False)
            if user.role == "journalist" and article_instance.is_rejected:
                article_instance.is_rejected = False
                article_instance.rejected_reason = None
                article_instance.rejected_by = None
                article_instance.rejected_date = None
            article_instance.save()
            messages.success(request, "Article updated successfully!")
            return redirect("article_detail", pk=article.pk)
    else:
        form = ArticleForm(instance=article, user=user)

    return render(
        request,
        "news_app/article_form.html",
        {"form": form, "article": article, "title": "Edit Article"},
    )


@login_required
def delete_article(request, pk):
    """
    Allow journalists to delete their own unapproved articles.

    :param request: HTTP request object
    :type request: HttpRequest
    :param pk: Primary key of the article
    :type pk: int
    :returns: Confirmation page or redirect after deletion
    :rtype: HttpResponse
    """
    article = get_object_or_404(Article, pk=pk)

    if article.author != request.user:
        messages.error(request, "You can only delete your own articles.")
        return redirect("my_articles")

    if article.is_approved:
        messages.error(request, "Cannot delete approved articles. Please contact an editor.")
        return redirect("my_articles")

    if request.method == "POST":
        article.delete()
        messages.success(request, "Article deleted successfully!")
        return redirect("my_articles")

    return render(request, "news_app/article_confirm_delete.html", {"article": article})


@login_required
def my_articles(request):
    """
    Display list of articles created by the logged-in journalist.

    :param request: HTTP request object
    :type request: HttpRequest
    :returns: Rendered list of journalist's articles
    :rtype: HttpResponse
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


@login_required
def create_newsletter(request):
    """
    Allow journalists to create new newsletters.

    :param request: HTTP request object
    :type request: HttpRequest
    :returns: Rendered form or redirect after creation
    :rtype: HttpResponse
    """
    if request.user.role != "journalist":
        messages.error(request, "Only journalists can create newsletters.")
        return redirect("home")

    if request.method == "POST":
        form = NewsletterForm(request.POST, request.FILES, user=request.user)
        form.instance.author = request.user
        if form.is_valid():
            newsletter = form.save(commit=False)
            newsletter.save()
            messages.success(request, "Newsletter created successfully!")
            return redirect("my_newsletters")
    else:
        form = NewsletterForm(user=request.user)

    return render(
        request,
        "news_app/newsletter_form.html",
        {"form": form, "title": "Create New Newsletter"},
    )


@login_required
def edit_newsletter(request, pk):
    """
    Allow journalists to edit their own newsletters.

    :param request: HTTP request object
    :type request: HttpRequest
    :param pk: Primary key of the newsletter
    :type pk: int
    :returns: Rendered form or redirect after saving
    :rtype: HttpResponse
    """
    newsletter = get_object_or_404(Newsletter, pk=pk)

    if newsletter.author != request.user:
        messages.error(request, "You can only edit your own newsletters.")
        return redirect("my_newsletters")

    if request.method == "POST":
        form = NewsletterForm(request.POST, instance=newsletter, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Newsletter updated successfully!")
            return redirect("my_newsletters")
    else:
        form = NewsletterForm(instance=newsletter, user=request.user)

    return render(
        request,
        "news_app/newsletter_form.html",
        {"form": form, "newsletter": newsletter, "title": "Edit Newsletter"},
    )


@login_required
def delete_newsletter(request, pk):
    """
    Allow journalists to delete their own newsletters.

    :param request: HTTP request object.
    :param pk: Primary key of the newsletter.
    :returns: Confirmation page or redirect after deletion.
    :rtype: HttpResponse
    """
    newsletter = get_object_or_404(Newsletter, pk=pk)

    if newsletter.author != request.user:
        messages.error(request, "You can only delete your own newsletters.")
        return redirect("my_newsletters")

    if request.method == "POST":
        newsletter.delete()
        messages.success(request, "Newsletter deleted successfully!")
        return redirect("my_newsletters")

    return render(
        request,
        "news_app/newsletter_confirm_delete.html",
        {"newsletter": newsletter},
    )


@login_required
def my_newsletters(request):
    """
    Display list of newsletters created by the logged-in journalist.

    :param request: HTTP request object.
    :returns: Rendered list of journalist's newsletters.
    :rtype: HttpResponse
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
    """
    Display list of all newsletters.

    :param: None
    :returns: ListView rendering newsletters.
    """
    model = Newsletter
    template_name = "news_app/newsletter_list.html"
    context_object_name = "newsletters"
    paginate_by = 10

    def get_queryset(self):
        """
        Get queryset of newsletters.

        :returns: QuerySet of newsletters.
        """
        return (
            Newsletter.objects.all()
            .select_related("author", "publisher")
            .order_by("-published_date")
        )


class NewsletterDetailView(DetailView):
    """
    Display detailed view of a single newsletter.

    Shows full newsletter content, author information, and subscription
    options for authenticated users.

    :ivar model: Newsletter model class
    :ivar template_name: Template to render
    :ivar context_object_name: Name of newsletter object in template
    """
    model = Newsletter
    template_name = "news_app/newsletter_detail.html"
    context_object_name = "newsletter"

    def get_context_data(self, **kwargs):
        """
        Add related newsletters to context.

        :param kwargs: Additional context kwargs.
        :returns: Context dictionary.
        """
        context = super().get_context_data(**kwargs)
        context["related_newsletters"] = (
            Newsletter.objects.filter(author=self.object.author)
            .exclude(pk=self.object.pk)
            .order_by("-published_date")[:5]
        )
        return context


class ArticleListView(ListView):
    """
    Display list of approved articles.

    Shows paginated list of all approved articles, ordered by
    publication date (newest first).

    :ivar model: Article model class
    :ivar template_name: Template to render
    :ivar context_object_name: Name of articles queryset in template
    :ivar paginate_by: Number of articles per page
    """
    model = Article
    template_name = "news_app/article_list.html"
    context_object_name = "articles"
    paginate_by = 10

    def get_queryset(self):
        """
        Return only approved articles.
        """
        return (
            Article.objects.filter(is_approved=True)
            .select_related("author", "publisher")
            .order_by("-published_date")
        )


class ArticleDetailView(DetailView):
    """
    Display detailed view of a single article.

    Shows full article content with permissions:
    - Public: Only approved articles
    - Editors: All articles
    - Journalists: Approved articles + their own articles

    :ivar model: Article model class
    :ivar template_name: Template to render
    :ivar context_object_name: Name of article object in template
    """
    model = Article
    template_name = "news_app/article_detail.html"
    context_object_name = "article"

    def get_queryset(self):
        """
        Return articles based on user permissions.
        """
        user = self.request.user
        if not user.is_authenticated:
            return Article.objects.filter(is_approved=True)
        if user.role == "editor":
            return Article.objects.all()
        if user.role == "journalist":
            return Article.objects.filter(Q(is_approved=True) | Q(author=user))
        return Article.objects.filter(is_approved=True)


class PendingArticlesView(LoginRequiredMixin, ListView):
    """
    Display list of articles pending approval (editors only).

    Shows all articles that are not yet approved or rejected,
    allowing editors to review and approve/reject them.

    :ivar model: Article model class
    :ivar template_name: Template to render
    :ivar context_object_name: Name of articles queryset in template
    :ivar paginate_by: Number of articles per page
    """
    model = Article
    template_name = "news_app/pending_articles.html"
    context_object_name = "articles"

    def dispatch(self, request, *args, **kwargs):
        """
        Ensure user is an editor.
        """
        if not request.user.is_authenticated:
            return redirect("login")
        if request.user.role != "editor":
            return redirect("article_list")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        """
        Return unapproved, not rejected articles.
        """
        return (
            Article.objects.filter(is_approved=False, is_rejected=False)
            .select_related("author", "publisher")
            .order_by("-created_at")
        )


@login_required
def approve_article(request, pk):
    """
    Approve an article for publication.

    :param request: HTTP request object.
    :param pk: Primary key of the article.
    :returns: Redirect or rendered confirmation.
    :rtype: HttpResponse
    """
    article = get_object_or_404(Article, pk=pk)

    if article.is_rejected:
        messages.error(request, "This article was rejected and cannot be approved.")
        return redirect("pending_articles")

    if article.is_approved:
        messages.info(request, "This article is already approved.")
        return redirect("pending_articles")

    if request.method == "POST":
        article.is_approved = True
        article.approved_by = request.user
        article.approval_date = timezone.now()
        article.published_date = timezone.now()
        article.save()
        return redirect("pending_articles")

    return render(request, "news_app/approve_article.html", {"article": article})


@login_required
def reject_article(request, pk):
    """
    Reject an article and record reason.

    :param request: HTTP request object.
    :param pk: Primary key of the article.
    :returns: Redirect after rejection or rendered form.
    :rtype: HttpResponse
    """
    article = get_object_or_404(Article, pk=pk)

    if request.method == "POST":
        article.is_approved = False
        article.is_rejected = True
        article.rejected_by = request.user
        article.rejected_date = timezone.now()
        article.rejected_reason = request.POST.get("reason", "")
        article.save()
        messages.success(request, "Article rejected.")
        return redirect("pending_articles")

    return render(request, "news_app/reject_article.html", {"article": article})


@login_required
def publish_independently(request, pk):
    """
    Publish an article independently by its author.

    :param request: HTTP request object.
    :param pk: Primary key of the article.
    :returns: Rendered my_articles page with message.
    :rtype: HttpResponse
    """
    article = get_object_or_404(Article, pk=pk, author=request.user)
    article.independently_published = True
    article.is_approved = True
    article.approval_date = timezone.now()
    article.published_date = timezone.now()
    article.save()
    messages.success(request, "Your article has been published independently.")
    return render(request, "news_app/my_articles.html", {"article": article})


@login_required
def dashboard(request):
    """
    Display role-specific dashboard.

    :param request: HTTP request object.
    :returns: Rendered dashboard page.
    :rtype: HttpResponse
    """
    user = request.user
    context = {"user": user}

    if user.role == "reader":
        context["subscribed_newsletters"] = user.subscribed_newsletters.all()
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
        context["total_newsletters"] = user.independent_newsletters.count()

    return render(request, "news_app/dashboard.html", context)


@login_required
def create_publisher(request):
    """
    Allow users with 'publisher' role to create a Publisher.

    :param request: HTTP request object.
    :returns: Rendered form or redirect after creation.
    :rtype: HttpResponse
    """
    if request.user.role != "publisher":
        messages.error(request, "Only users with publisher role can create publishers.")
        return redirect("home")

    # Prevent a publisher user from having multiple publishers
    existing_publisher = Publisher.objects.filter(owner=request.user).first()
    if existing_publisher:
        messages.info(request, f"You already own {existing_publisher.name}.")
        return redirect("publisher_dashboard", pk=existing_publisher.pk)

    if request.method == "POST":
        form = PublisherForm(request.POST)
        if form.is_valid():
            publisher = form.save(commit=False)

            # ⭐ AUTO-ASSIGN OWNER
            publisher.owner = request.user
            publisher.save()

            messages.success(
                request,
                f'Publisher "{publisher.name}" created successfully! You are now the owner.'
            )
            return redirect("publisher_dashboard", pk=publisher.pk)
    else:
        form = PublisherForm()

    return render(
        request,
        "news_app/publisher_form.html",
        {"form": form, "title": "Create Publisher"},
    )


def publisher_list(request):
    """
    Display list of all publishers.

    :param request: HTTP request object.
    :returns: Rendered publisher list page.
    :rtype: HttpResponse
    """
    publishers = Publisher.objects.all().order_by("-created_at")
    return render(request, "news_app/publisher_list.html", {"publishers": publishers})


def publisher_detail(request, pk):
    """
    Display detailed view of a single publisher.

    :param request: HTTP request object.
    :param pk: Primary key of the publisher.
    :returns: Rendered publisher detail page.
    :rtype: HttpResponse
    """
    publisher = get_object_or_404(Publisher, pk=pk)
    recent_articles = (
        Article.objects.filter(publisher=publisher, is_approved=True)
        .select_related("author")
        .order_by("-published_date")[:10]
    )

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


@login_required
def request_join_publisher(request, pk):
    publisher = get_object_or_404(Publisher, pk=pk)

    # Only journalists/editors can join
    if request.user.role not in ["journalist", "editor"]:
        messages.error(request, "Only journalists and editors can request to join.")
        return redirect("publisher_detail", pk=pk)

    # Prevent multiple active requests
    if PublisherJoinRequest.objects.filter(
        user=request.user, publisher=publisher, status="pending"
    ).exists():
        messages.warning(request, "You already submitted a request to this publisher.")
        return redirect("publisher_detail", pk=pk)

    if request.method == "POST":
        message = request.POST.get("message")
        portfolio = request.POST.get("portfolio")

        PublisherJoinRequest.objects.create(
            user=request.user,
            publisher=publisher,
            message=message,
        )

        messages.success(request, "Your request has been submitted!")
        return redirect("publisher_detail", pk=pk)

    return render(request, "news_app/request_join_publisher.html", {"publisher": publisher})

@login_required
def publisher_join_requests(request):
    """
    Display all join requests (pending, approved, rejected) for a publisher.

    Publishers can view and manage join requests for their publisher
    organization.
    """
    publisher = Publisher.objects.filter(owner=request.user).first()
    if not publisher:
        messages.error(
            request,
            "You must be a publisher owner to view join requests."
        )
        return redirect("dashboard")

    # Get filter parameter (default to 'pending')
    status_filter = request.GET.get("status", "pending")

    # Validate status filter
    valid_statuses = ["pending", "approved", "rejected", "all"]
    if status_filter not in valid_statuses:
        status_filter = "pending"

    # Get all requests for this publisher
    all_requests = (
        PublisherJoinRequest.objects.filter(publisher=publisher)
        .select_related("user", "reviewed_by")
        .order_by("-created_at")
    )

    # Filter by status
    if status_filter == "all":
        requests_list = all_requests
    else:
        requests_list = all_requests.filter(status=status_filter)

    # Count requests by status
    pending_count = all_requests.filter(status="pending").count()
    approved_count = all_requests.filter(status="approved").count()
    rejected_count = all_requests.filter(status="rejected").count()
    total_count = all_requests.count()

    context = {
        "publisher": publisher,
        "requests_list": requests_list,
        "status_filter": status_filter,
        "pending_count": pending_count,
        "approved_count": approved_count,
        "rejected_count": rejected_count,
        "total_count": total_count,
    }

    return render(request, "news_app/publisher_join_requests.html", context)

    


@login_required
def publisher_dashboard(request, pk):
    """
    Display publisher dashboard for editors.

    :param request: HTTP request object.
    :param pk: Primary key of the publisher.
    :returns: Rendered dashboard page.
    :rtype: HttpResponse
    """
    publisher = get_object_or_404(Publisher, pk=pk)

    # Who can access this dashboard
    is_owner = (publisher.owner == request.user)
    is_editor = publisher.editors.filter(pk=request.user.pk).exists()

    # Only owner OR editor can open dashboard
    if not (is_owner or is_editor):
        messages.error(request, "You do not have permission to access this publisher dashboard.")
        return redirect("publisher_detail", pk=pk)

    # Only show join requests if user is the OWNER
    pending_requests = []
    if is_owner:
        pending_requests = PublisherJoinRequest.objects.filter(
            publisher=publisher,
            status="pending"
        ).select_related("user")

    members = list(publisher.editors.all()) + list(publisher.journalists.all())

    context = {
        "publisher": publisher,
        "is_owner": is_owner,   # <—— template needs this
        "pending_requests": pending_requests,
        "editors": publisher.editors.all(),
        "journalists": publisher.journalists.all(),
        "articles": publisher.articles.all()[:10],
        "members": members,
    }

    return render(request, "news_app/publisher_dashboard.html", context)




@login_required
def approve_join_request(request, request_id):
    """
    Approve a join request to a publisher.

    :param request: HTTP request object.
    :param request_id: Primary key of the join request.
    :returns: Redirect to publisher dashboard.
    :rtype: HttpResponse
    """
    join_req = get_object_or_404(PublisherJoinRequest, id=request_id)

    # Only the publisher owner can approve
    if request.user != join_req.publisher.owner:
        messages.error(
            request,
            "You are not allowed to approve this request."
        )
        return redirect("publisher_dashboard", pk=join_req.publisher.pk)

    # Update join request
    join_req.status = "approved"
    join_req.reviewed_by = request.user
    join_req.reviewed_at = timezone.now()
    join_req.save()

    if join_req.user.role == "journalist":
        join_req.publisher.journalists.add(join_req.user)
    elif join_req.user.role == "editor":
        join_req.publisher.editors.add(join_req.user)

    messages.success(
        request,
        f"{join_req.user.username} has been added to the team."
    )
    return redirect("publisher_join_requests")

@login_required
def reject_join_request(request, request_id):
    """
    Reject a join request to a publisher.

    :param request: HTTP request object.
    :param request_id: Primary key of the join request.
    :returns: Redirect to publisher dashboard.
    :rtype: HttpResponse
    """
    join_req = get_object_or_404(PublisherJoinRequest, id=request_id)

    if request.user != join_req.publisher.owner:
        messages.error(
            request,
            "You are not allowed to approve this request."
        )
        return redirect("publisher_dashboard", pk=join_req.publisher.pk)

    join_req.status = "rejected"
    join_req.reviewed_by = request.user
    join_req.reviewed_at = timezone.now()
    join_req.save()

    messages.success(
        request,
        f"Join request from {join_req.user.username} has been rejected."
    )
    return redirect("publisher_join_requests")

    if join_req.user.role == "journalist":
        join_req.publisher.journalists.add(join_req.user)
    elif join_req.user.role == "editor":
        join_req.publisher.editors.add(join_req.user)

    messages.info(request, f"{join_req.user.username}'s request was rejected.")
    return redirect("publisher_join_requests")


@login_required
def web_subscribe_to_journalist(request, journalist_id):
    """
    Subscribe to a journalist (HTML view).

    :param request: HTTP request object.
    :param journalist_id: ID of the journalist.
    :returns: Redirect back to journalist list.
    :rtype: HttpResponse
    """
    if request.user.role != "reader":
        messages.error(request, "Only readers may subscribe to journalists.")
        return redirect("journalist_list")

    journalist = get_object_or_404(CustomUser, id=journalist_id, role="journalist")

    if journalist in request.user.subscribed_journalists.all():
        messages.info(request, f"You are already subscribed to {journalist.username}.")
    else:
        request.user.subscribed_journalists.add(journalist)
        messages.success(request, f"Subscribed to {journalist.username}!")

    return redirect("journalist_list")


@login_required
def web_unsubscribe_from_journalist(request, journalist_id):
    """
    Unsubscribe from a journalist (HTML view).

    :param request: HTTP request object.
    :param journalist_id: ID of the journalist.
    :returns: Redirect back to journalist list.
    :rtype: HttpResponse
    """
    if request.user.role != "reader":
        messages.error(request, "Only readers may unsubscribe.")
        return redirect("journalist_list")

    journalist = get_object_or_404(CustomUser, id=journalist_id, role="journalist")

    if journalist not in request.user.subscribed_journalists.all():
        messages.info(request, f"You were not subscribed to {journalist.username}.")
    else:
        request.user.subscribed_journalists.remove(journalist)
        messages.success(request, f"Unsubscribed from {journalist.username}.")

    return redirect("journalist_list")


@login_required
def subscribe_newsletter(request, newsletter_id):
    """
    Web interface to subscribe to a newsletter.

    :param request: HTTP request object.
    :param newsletter_id: ID of the newsletter.
    :returns: Redirect to newsletter detail.
    :rtype: HttpResponse
    """
    if request.user.role not in ["reader", "editor"]:
        messages.error(request, "Only readers and editors can subscribe to newsletters.")
        return redirect("newsletter_detail", pk=newsletter_id)

    newsletter = get_object_or_404(Newsletter, id=newsletter_id)

    if newsletter in request.user.subscribed_newsletters.all():
        messages.info(request, f"You are already subscribed to {newsletter.title}.")
    else:
        request.user.subscribed_newsletters.add(newsletter)
        messages.success(request, f"Successfully subscribed to {newsletter.title}!")

    return redirect("newsletter_detail", pk=newsletter_id)


@login_required
def unsubscribe_newsletter(request, newsletter_id):
    """
    Web interface to unsubscribe from a newsletter.

    :param request: HTTP request object.
    :param newsletter_id: ID of the newsletter.
    :returns: Redirect to newsletter detail.
    :rtype: HttpResponse
    """
    if request.user.role not in ["reader", "editor"]:
        messages.error(request, "Only readers and editors can manage newsletter subscriptions.")
        return redirect("newsletter_detail", pk=newsletter_id)

    newsletter = get_object_or_404(Newsletter, id=newsletter_id)

    if newsletter not in request.user.subscribed_newsletters.all():
        messages.info(request, f"You are not subscribed to {newsletter.title}.")
    else:
        request.user.subscribed_newsletters.remove(newsletter)
        messages.success(request, f"Successfully unsubscribed from {newsletter.title}.")

    return redirect("newsletter_detail", pk=newsletter_id)


@login_required
def subscription_dashboard(request):
    """
    Display user's subscriptions dashboard.

    :param request: HTTP request object.
    :returns: Rendered subscription dashboard.
    :rtype: HttpResponse
    """
    if request.user.role not in ["reader", "editor"]:
        messages.error(request, "Only readers and editors have subscriptions.")
        return redirect("home")

    context = {
        "subscribed_newsletters": request.user.subscribed_newsletters.all(),
        "subscribed_publishers": request.user.subscribed_publishers.all(),
        "subscribed_journalists": request.user.subscribed_journalists.all(),
        "title": "My Subscriptions",
    }
    return render(request, "news_app/subscription_dashboard.html", context)


def journalist_list(request):
    """
    Display list of all journalists.

    :param request: HTTP request object.
    :returns: Rendered journalist list page.
    :rtype: HttpResponse
    """
    journalists = CustomUser.objects.filter(role="journalist").order_by("username")
    return render(request, "news_app/journalist_list.html", {"journalists": journalists, "title": "Journalists"})


class ArticleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Article CRUD operations via API.

    Provides full CRUD functionality for articles with role-based
    permissions:
    - Journalists: Can create articles
    - Editors: Can update/delete any article
    - All authenticated users: Can view approved articles

    :ivar queryset: Base queryset for articles
    :ivar permission_classes: Base permission classes
    """
    queryset = Article.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """
        Return serializer class depending on action.

        :returns: ArticleCreateSerializer for create action, ArticleSerializer for all other actions
        :rtype: class
        """
        if self.action == "create":
            return ArticleCreateSerializer
        return ArticleSerializer

    def get_queryset(self):
        """
        Return articles filtered by user role.

        :returns: Filtered articles based on user role (Editors: All articles, Journalists: Approved + own, Others: Approved only)
        :rtype: QuerySet
        """
        user = self.request.user
        if user.role == "editor":
            return Article.objects.all()
        if user.role == "journalist":
            return Article.objects.filter(Q(is_approved=True) | Q(author=user))
        return Article.objects.filter(is_approved=True)

    def get_permissions(self):
        """
        Return permission instances for actions.

        Returns:
            list: Permission classes based on action:
                - create: IsJournalist
                - update/partial_update/destroy: IsEditor
                - Other: IsAuthenticated
        """
        if self.action == "create":
            return [IsJournalist()]
        if self.action in ["update", "partial_update", "destroy"]:
            return [IsEditor()]
        return [IsAuthenticated()]


class NewsletterViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Newsletter CRUD operations via API.

    Provides full CRUD functionality for newsletters with role-based
    permissions:
    - Journalists: Can create newsletters
    - Editors: Can update/delete any newsletter
    - All authenticated users: Can view newsletters

    :ivar queryset: Base queryset for newsletters
    :ivar permission_classes: Base permission classes
    """
    queryset = Newsletter.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """
        Return serializer class depending on action.

        :returns: NewsletterCreateSerializer for create action, NewsletterSerializer for all other actions
        :rtype: class
        """
        if self.action == "create":
            return NewsletterCreateSerializer
        return NewsletterSerializer

    def get_permissions(self):
        """
        Return permission instances for actions.

        :returns: Permission classes based on action (create: IsJournalist, update/delete: IsEditor, other: IsAuthenticated)
        :rtype: list
        """
        if self.action == "create":
            return [IsJournalist()]
        if self.action in ["update", "partial_update", "destroy"]:
            return [IsEditor()]
        return [IsAuthenticated()]


class PublisherViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Publisher read-only operations via API.

    Provides read-only access to publishers. Includes custom action
    to retrieve articles for a specific publisher.

    :ivar queryset: Base queryset for publishers
    :ivar serializer_class: Serializer for publisher data
    :ivar permission_classes: Base permission classes
    """
    queryset = Publisher.objects.all()
    serializer_class = PublisherSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=["get"])
    def articles(self, request, pk=None):
        """
        Get approved articles for a specific publisher.

        Custom API action to retrieve all approved articles
        published by a specific publisher.

        :param request: HTTP request object
        :type request: HttpRequest
        :param pk: Primary key of the publisher
        :type pk: int
        :returns: Paginated list of approved articles
        :rtype: Response
        """
        publisher = self.get_object()
        articles = Article.objects.filter(publisher=publisher, is_approved=True).order_by("-published_date")
        page = self.paginate_queryset(articles)
        if page is not None:
            serializer = ArticleSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = ArticleSerializer(articles, many=True)
        return Response(serializer.data)


class JournalistArticlesView(generics.ListAPIView):
    """
    API view to retrieve articles by a specific journalist.

    Returns a paginated list of approved articles authored by
    the specified journalist.

    :ivar serializer_class: Serializer for article data
    :ivar permission_classes: Permission classes required
    """
    serializer_class = ArticleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Get queryset of approved articles by journalist.

        :returns: Approved articles by the specified journalist, ordered by publication date (newest first)
        :rtype: QuerySet
        """
        journalist_id = self.kwargs.get("journalist_id")
        return Article.objects.filter(author_id=journalist_id, is_approved=True).order_by("-published_date")


class SubscriptionArticlesView(generics.ListAPIView):
    """
    API view for retrieving articles based on user subscriptions.

    Returns articles from publishers and journalists that the
    authenticated reader is subscribed to. Only available to readers.

    :ivar serializer_class: Serializer for subscription article data
    :ivar permission_classes: Permission classes required
    """
    serializer_class = SubscriptionArticleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Get queryset of articles from user's subscriptions.

        :returns: Approved articles from subscribed publishers and journalists, ordered by publication date. Returns empty queryset if user is not a reader
        :rtype: QuerySet
        """
        user = self.request.user
        if user.role != "reader":
            return Article.objects.none()
        subscribed_publishers = user.subscribed_publishers.all()
        subscribed_journalists = user.subscribed_journalists.all()
        articles = (
            Article.objects.filter(
                Q(publisher__in=subscribed_publishers) | Q(author__in=subscribed_journalists),
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

    :param request: HTTP request object
    :type request: HttpRequest
    :param publisher_id: ID of the publisher to subscribe to
    :type publisher_id: int
    :returns: JSON response indicating success or error
    :rtype: Response
    """
    if request.user.role != "reader":
        return Response({"error": "Only readers can subscribe to publishers"}, status=status.HTTP_403_FORBIDDEN)

    publisher = get_object_or_404(Publisher, id=publisher_id)
    if publisher in request.user.subscribed_publishers.all():
        return Response({"message": f"Already subscribed to {publisher.name}"}, status=status.HTTP_200_OK)

    request.user.subscribed_publishers.add(publisher)
    return Response(
        {"message": f"Successfully subscribed to {publisher.name}", "publisher": {"id": publisher.id, "name": publisher.name}},
        status=status.HTTP_201_CREATED,
    )


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def unsubscribe_from_publisher(request, publisher_id):
    """
    Unsubscribe the authenticated user from a publisher.

    :param request: HTTP request object
    :type request: HttpRequest
    :param publisher_id: ID of the publisher to unsubscribe from
    :type publisher_id: int
    :returns: JSON response indicating success or error
    :rtype: Response
    """
    if request.user.role != "reader":
        return Response({"error": "Only readers can manage subscriptions"}, status=status.HTTP_403_FORBIDDEN)

    publisher = get_object_or_404(Publisher, id=publisher_id)
    if publisher not in request.user.subscribed_publishers.all():
        return Response({"message": f"Not subscribed to {publisher.name}"}, status=status.HTTP_200_OK)

    request.user.subscribed_publishers.remove(publisher)
    return Response({"message": f"Successfully unsubscribed from {publisher.name}"}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def subscribe_to_journalist(request, journalist_id):
    """
    Subscribe the authenticated user to a journalist.

    :param request: HTTP request object
    :type request: HttpRequest
    :param journalist_id: ID of the journalist to subscribe to
    :type journalist_id: int
    :returns: JSON response indicating success or error
    :rtype: Response
    """
    if request.user.role != "reader":
        return Response({"error": "Only readers can subscribe to journalists"},
                        status=status.HTTP_403_FORBIDDEN)

    journalist = get_object_or_404(CustomUser, id=journalist_id,
                                   role="journalist")
    if journalist in request.user.subscribed_journalists.all():
        return Response({"message": f"Already subscribed to {journalist.username}"}, status=status.HTTP_200_OK)

    request.user.subscribed_journalists.add(journalist)
    return Response(
        {"message": f"Successfully subscribed to {journalist.username}",
         "journalist": {"id": journalist.id, "username": journalist.username}},
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def unsubscribe_from_journalist(request, journalist_id):
    """
    Unsubscribe the authenticated user from a journalist.

    :param request: HTTP request object
    :type request: HttpRequest
    :param journalist_id: ID of the journalist to unsubscribe from
    :type journalist_id: int
    :returns: JSON response indicating success or error
    :rtype: Response
    """
    if request.user.role != "reader":
        return Response({"error": "Only readers can manage subscriptions"}, status=status.HTTP_403_FORBIDDEN)

    journalist = get_object_or_404(CustomUser, id=journalist_id, role="journalist")
    if journalist not in request.user.subscribed_journalists.all():
        return Response({"message": f"Not subscribed to {journalist.username}"}, status=status.HTTP_200_OK)

    request.user.subscribed_journalists.remove(journalist)
    return Response({"message": f"Successfully unsubscribed from {journalist.username}"}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_subscriptions(request):
    """
    Get all subscriptions for the authenticated user.

    Returns a list of all publishers and journalists the user
    is subscribed to. Only available to readers.

    :param request: HTTP request object
    :type request: HttpRequest
    :returns: JSON response with lists of subscribed publishers and journalists, or error if user is not a reader
    :rtype: Response
    """
    if request.user.role != "reader":
        return Response({"error": "Only readers have subscriptions"}, status=status.HTTP_403_FORBIDDEN)

    publishers = request.user.subscribed_publishers.all()
    journalists = request.user.subscribed_journalists.all()

    return Response(
        {
            "publishers": [
                {"id": p.id, "name": p.name, "description": p.description, "website": p.website}
                for p in publishers
            ],
            "journalists": [
                {"id": j.id, "username": j.username, "email": j.email, "full_name": j.get_full_name()}
                for j in journalists
            ],
        }
    )
