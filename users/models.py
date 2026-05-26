import io
import random

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.files.base import ContentFile
from django.db import models
from PIL import Image, ImageDraw, ImageFont

# Field length limits (from spec)
USER_NAME_MAX_LENGTH = 124
USER_PHONE_MAX_LENGTH = 12
USER_ABOUT_MAX_LENGTH = 256

# Auto-generated avatar dimensions
AVATAR_SIZE = 100
AVATAR_FONT_SIZE = 50

AVATAR_COLORS = [
    '#4A90D9', '#7B68EE', '#20B2AA', '#3CB371', '#FF8C00',
    '#9370DB', '#5F6B7C', '#4682B4', '#008080', '#6B8E23',
]


def _generate_avatar(letter: str) -> ContentFile:
    color = random.choice(AVATAR_COLORS)
    img = Image.new('RGB', (AVATAR_SIZE, AVATAR_SIZE), color)
    draw = ImageDraw.Draw(img)
    text = letter[0].upper() if letter else '?'

    try:
        font = ImageFont.truetype('arial.ttf', AVATAR_FONT_SIZE)
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x = (AVATAR_SIZE - w) / 2 - bbox[0]
    y = (AVATAR_SIZE - h) / 2 - bbox[1]
    draw.text((x, y), text, fill='white', font=font)

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return ContentFile(buf.getvalue())


class UserManager(BaseUserManager):
    def create_user(self, email, name, surname, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, name=name, surname=surname, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, surname, password=None, **extra_fields):
        extra_fields['is_staff'] = True
        extra_fields['is_superuser'] = True
        extra_fields['is_active'] = True
        return self.create_user(email, name, surname, password, **extra_fields)


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
            avatar_file = _generate_avatar(letter)
            safe = self.email.replace('@', '_').replace('.', '_')
            self.avatar.save(f'avatar_{safe}.png', avatar_file, save=False)
        super().save(*args, **kwargs)
