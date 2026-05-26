from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from utils import generate_avatar
from .managers import UserManager

# Field length limits (from spec)
USER_NAME_MAX_LENGTH = 124
USER_PHONE_MAX_LENGTH = 12
USER_ABOUT_MAX_LENGTH = 256


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=USER_NAME_MAX_LENGTH)
    surname = models.CharField(max_length=USER_NAME_MAX_LENGTH)
    avatar = models.ImageField(upload_to='avatars/', blank=True)
    phone = models.CharField(max_length=USER_PHONE_MAX_LENGTH, blank=True)
    github_url = models.URLField(blank=True)
    about = models.TextField(max_length=USER_ABOUT_MAX_LENGTH, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name', 'surname']

    objects = UserManager()

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return f'{self.name} {self.surname} ({self.email})'

    def save(self, *args, **kwargs):
        if not self.pk and not self.avatar:
            letter = self.name[0] if self.name else '?'
            avatar_file = generate_avatar(letter)
            safe = self.email.replace('@', '_').replace('.', '_')
            self.avatar.save(f'avatar_{safe}.png', avatar_file, save=False)
        super().save(*args, **kwargs)
