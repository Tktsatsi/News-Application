from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import Article, Newsletter, Publisher

User = get_user_model()


class UserRegistrationForm(UserCreationForm):
    """
    Form for user registration with role selection.

    Extends Django's UserCreationForm to include email and role fields.
    Users can register as Reader, Journalist, Editor, or Publisher.

    :ivar email: Email field (required)
    :ivar role: Role selection field with radio buttons
    """
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(
        choices=[
            ("reader", "Reader"),
            ("journalist", "Journalist"),
            ("editor", "Editor"),
            ("publisher", "Publisher"),
        ],
        widget=forms.RadioSelect,
        required=True,
        label="Register as",
    )

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2", "role"]

    def save(self, commit=True):
        """
        Save the user with email and role.

        :param commit: Whether to save to database immediately
        :type commit: bool
        :returns: The created user instance
        :rtype: CustomUser
        """
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.role = self.cleaned_data["role"]

        if commit:
            user.save()
        return user


class NewsletterForm(forms.ModelForm):
    """
    Form for creating and editing newsletters.

    Allows journalists to create newsletters independently or
    associate them with a publisher they belong to.

    :ivar Meta: Form metadata including model and fields
    """

    class Meta:
        model = Newsletter
        fields = ["title", "content", "publisher"]
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter newsletter title"}
            ),
            "content": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Write your newsletter content here...",
                    "rows": 10,
                }
            ),
            "publisher": forms.Select(),
        }

    def __init__(self, *args, **kwargs):
        """
        Initialize form and set publisher queryset based on user membership.

        Filters available publishers based on user's role and membership.
        For journalists, only shows publishers they belong to.

        :param args: Variable length argument list
        :param kwargs: Arbitrary keyword arguments (user is extracted)
        """
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Make publisher optional (allows independent newsletters)
        self.fields["publisher"].required = False
        self.fields["publisher"].empty_label = "Independent (No Publisher)"

        # Filter publishers based on user's membership
        if user and user.role == "journalist":
            # Show only publishers where this journalist is a member
            self.fields["publisher"].queryset = Publisher.objects.filter(
                journalists=user
            ).order_by("name")
        else:
            # For other users (or no user), show all publishers
            self.fields["publisher"].queryset = Publisher.objects.all().order_by("name")


class PublisherForm(forms.ModelForm):
    """
    Form for creating publishers.

    Allows users with publisher role to create publisher organizations
    with name, description, website, and established date.

    :ivar Meta: Form metadata including model and fields
    """

    class Meta:
        model = Publisher
        fields = ["name", "description", "website", "established_date"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Publisher name"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Brief description of the publisher",
                    "rows": 3,
                }
            ),
            "website": forms.URLInput(
                attrs={"class": "form-control", "placeholder": "https://example.com"}
            ),
            "established_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
        }


class ArticleForm(forms.ModelForm):
    """
    Form for creating and updating articles.

    Available to journalists and publishers.
    """

    publisher = forms.ModelChoiceField(
        queryset=Publisher.objects.all().order_by("name"),
        required=False,
        empty_label="Independent (No Publisher)",
        help_text=(
            "Select a publisher or leave blank for independent article"
        ),
        widget=forms.Select(attrs={
            "class": "form-control",
            "style": "width: 100%;"
        })
    )

    class Meta:
        model = Article
        fields = ["title", "content", "publisher", "image", "summary"]
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter article title"
            }),
            "content": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 15,
                "placeholder": "Write your article content here..."
            }),
            "summary": forms.Select(attrs={
                "class": "form-control"
            }),
            "image": forms.FileInput(attrs={
                "class": "form-control",
                "accept": "image/*"
            }),
        }
        labels = {
            "title": "Article Title",
            "content": "Article Content",
            "publisher": "Publisher",
            "image": "Featured Image (Optional)",
            "summary": "Summary",
        }

    def __init__(self, *args, **kwargs):
        """
        Initialize form and configure publisher field.

        Sets up publisher field to be optional and auto-selects
        publisher if user belongs to one.

        :param args: Variable length argument list
        :param kwargs: Arbitrary keyword arguments (user is extracted)
        """
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Make publisher optional (allows independent articles)
        self.fields["publisher"].required = False
        self.fields["publisher"].empty_label = "Independent (No Publisher)"

        # Ensure all publishers are shown
        self.fields["publisher"].queryset = (
            Publisher.objects.all().order_by("name")
        )

        # Auto-select publisher if user belongs to one
        if user and user.role == "publisher" and user.publisher:
            self.fields["publisher"].initial = user.publisher