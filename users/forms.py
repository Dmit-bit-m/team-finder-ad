from django import forms
from django.core.exceptions import ValidationError

from utils import validate_github_url, validate_phone
from .models import User


class RegisterForm(forms.Form):
    name = forms.CharField(max_length=124, label='Имя')
    surname = forms.CharField(max_length=124, label='Фамилия')
    email = forms.EmailField(label='Email')
    password = forms.CharField(widget=forms.PasswordInput, label='Пароль')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('Пользователь с таким email уже зарегистрирован')
        return email


class LoginForm(forms.Form):
    email = forms.EmailField(label='Email')
    password = forms.CharField(widget=forms.PasswordInput, label='Пароль')

    def clean(self):
        from django.contrib.auth import authenticate
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')
        if email and password:
            user = authenticate(username=email, password=password)
            if user is None:
                raise ValidationError('Неверный email или пароль')
            cleaned_data['user'] = user
        return cleaned_data


class EditProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['name', 'surname', 'avatar', 'about', 'phone', 'github_url']
        labels = {
            'name': 'Имя',
            'surname': 'Фамилия',
            'avatar': 'Аватар',
            'about': 'О себе',
            'phone': 'Телефон',
            'github_url': 'GitHub',
        }
        widgets = {
            'avatar': forms.FileInput(attrs={'id': 'id_avatar', 'style': 'display:none'}),
        }

    def clean_phone(self):
        return validate_phone(
            self.cleaned_data.get('phone', ''),
            exclude_pk=self.instance.pk if self.instance else None,
        )

    def clean_github_url(self):
        return validate_github_url(self.cleaned_data.get('github_url', ''))


class ChangePasswordForm(forms.Form):
    old_password = forms.CharField(widget=forms.PasswordInput, label='Текущий пароль')
    new_password1 = forms.CharField(widget=forms.PasswordInput, label='Новый пароль')
    new_password2 = forms.CharField(widget=forms.PasswordInput, label='Подтвердите новый пароль')

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        old_password = cleaned_data.get('old_password')
        new_password1 = cleaned_data.get('new_password1')
        new_password2 = cleaned_data.get('new_password2')
        if old_password and not self.user.check_password(old_password):
            raise ValidationError('Неверный текущий пароль')
        if new_password1 and new_password2 and new_password1 != new_password2:
            raise ValidationError('Пароли не совпадают')
        return cleaned_data
