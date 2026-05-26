import re

from django.core.exceptions import ValidationError
from django.core.paginator import Paginator

# Pagination
PAGE_SIZE = 12

# Skills autocomplete
AUTOCOMPLETE_LIMIT = 10

# Phone validation patterns
_PHONE_RE_8 = re.compile(r'^8\d{10}$')
_PHONE_RE_PLUS7 = re.compile(r'^\+7\d{10}$')


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


def paginate_queryset(queryset, page_number, per_page: int = PAGE_SIZE):
    """Return a Page object for the given queryset and page number."""
    paginator = Paginator(queryset, per_page)
    return paginator.get_page(page_number)
