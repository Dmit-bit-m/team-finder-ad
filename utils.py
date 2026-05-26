import io
import random
import re

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.paginator import Paginator
from PIL import Image, ImageDraw, ImageFont

# Pagination
PAGE_SIZE = 12

# Auto-generated avatar dimensions
AVATAR_SIZE = 100
AVATAR_FONT_SIZE = 50

# Avatar background colors
AVATAR_COLOR_CORNFLOWER_BLUE = '#4A90D9'
AVATAR_COLOR_MEDIUM_SLATE_BLUE = '#7B68EE'
AVATAR_COLOR_LIGHT_SEA_GREEN = '#20B2AA'
AVATAR_COLOR_MEDIUM_SEA_GREEN = '#3CB371'
AVATAR_COLOR_DARK_ORANGE = '#FF8C00'
AVATAR_COLOR_MEDIUM_PURPLE = '#9370DB'
AVATAR_COLOR_SLATE_GRAY = '#5F6B7C'
AVATAR_COLOR_STEEL_BLUE = '#4682B4'
AVATAR_COLOR_TEAL = '#008080'
AVATAR_COLOR_OLIVE_DRAB = '#6B8E23'

AVATAR_COLORS = [
    AVATAR_COLOR_CORNFLOWER_BLUE,
    AVATAR_COLOR_MEDIUM_SLATE_BLUE,
    AVATAR_COLOR_LIGHT_SEA_GREEN,
    AVATAR_COLOR_MEDIUM_SEA_GREEN,
    AVATAR_COLOR_DARK_ORANGE,
    AVATAR_COLOR_MEDIUM_PURPLE,
    AVATAR_COLOR_SLATE_GRAY,
    AVATAR_COLOR_STEEL_BLUE,
    AVATAR_COLOR_TEAL,
    AVATAR_COLOR_OLIVE_DRAB,
]

# Skills autocomplete
AUTOCOMPLETE_LIMIT = 10

# Phone validation patterns
_PHONE_RE_8 = re.compile(r'^8\d{10}$')
_PHONE_RE_PLUS7 = re.compile(r'^\+7\d{10}$')


def generate_avatar(letter: str) -> ContentFile:
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


def validate_github_url(url: str) -> str:
    """Raise ValidationError unless the URL points to github.com."""
    if url and 'github.com' not in url:
        raise ValidationError('Ссылка должна вести на GitHub (github.com)')
    return url


def validate_phone(phone: str, exclude_pk=None) -> str:
    """Validate phone format (8XXXXXXXXXX or +7XXXXXXXXXX), normalise to +7, check uniqueness."""
    from django.contrib.auth import get_user_model

    phone = phone.strip()
    if not phone:
        return phone

    if _PHONE_RE_8.match(phone):
        phone = '+7' + phone[1:]
    elif not _PHONE_RE_PLUS7.match(phone):
        raise ValidationError(
            'Номер телефона должен быть в формате 8XXXXXXXXXX или +7XXXXXXXXXX'
        )

    User = get_user_model()
    qs = User.objects.filter(phone=phone)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    if qs.exists():
        raise ValidationError('Этот номер телефона уже используется')

    return phone


def paginate_queryset(queryset, request, per_page: int = PAGE_SIZE):
    """Return a Page object for the given queryset, reading page number from request.GET."""
    paginator = Paginator(queryset, per_page)
    return paginator.get_page(request.GET.get('page', 1))
