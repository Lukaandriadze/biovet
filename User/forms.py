from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password


class RegisterForm(forms.ModelForm):

    password = forms.CharField(
        widget=forms.PasswordInput,
        label="პაროლი"
    )

    password_confirm = forms.CharField(
        widget=forms.PasswordInput,
        label="გაიმეორეთ პაროლი"
    )

    class Meta:
        model = User
        fields = ["username", "email", "password"]

    def clean_username(self):
        username = self.cleaned_data["username"]

        if User.objects.filter(username=username).exists():
            raise forms.ValidationError(
                "ეს მომხმარებლის სახელი უკვე გამოყენებულია."
            )

        return username

    def clean_email(self):
        email = self.cleaned_data["email"]

        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                "ეს ელფოსტა უკვე გამოყენებულია."
            )

        return email

    def clean_password(self):
        password = self.cleaned_data["password"]

        validate_password(password)

        return password

    def clean(self):
        cleaned_data = super().clean()

        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm:

            if password != password_confirm:
                raise forms.ValidationError(
                    "პაროლები ერთმანეთს არ ემთხვევა."
                )

        return cleaned_data

    def save(self, commit=True):

        user = super().save(commit=False)

        user.set_password(
            self.cleaned_data["password"]
        )

        if commit:
            user.save()

        return user


class LoginForm(AuthenticationForm):

    username = forms.CharField(
        label="მომხმარებლის სახელი"
    )

    password = forms.CharField(
        widget=forms.PasswordInput,
        label="პაროლი"
    )