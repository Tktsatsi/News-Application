from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import Article, Newsletter, Publisher

User = get_user_model()


class UserRegistrationForm(UserCreationForm):
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
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.role = self.cleaned_data["role"]

        if commit:
            user.save()
        return user


class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = ["title", "content", "summary", "image", "publisher"]
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter article title"}
            ),
            "content": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Write your article content here...",
                    "rows": 10,
                }
            ),
            "summary": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Brief summary of the article",
                    "rows": 3,
                }
            ),
            "image": forms.FileInput(
                attrs={"class": "form-control", "accept": "image/*"}
            ),
            "publisher": forms.Select(),
        }

    def __init__(self, *args, **kwargs):
        """Initialize form and set publisher queryset based on user membership."""
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Make publisher optional (allows independent articles)
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


class NewsletterForm(forms.ModelForm):
    """Form for creating and editing newsletters."""

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
        """Initialize form and set publisher queryset based on user membership."""
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
    """Form for creating publishers."""

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
