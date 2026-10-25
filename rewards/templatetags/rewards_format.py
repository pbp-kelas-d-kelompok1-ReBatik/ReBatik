"""Formatting helpers for Indonesian point values and transaction dates."""

from django import template
from django.utils import timezone

register = template.Library()

MONTH_ABBREVIATIONS = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "Mei",
    "Jun",
    "Jul",
    "Agu",
    "Sep",
    "Okt",
    "Nov",
    "Des",
)


@register.filter
def intcomma_id(value):
    """Format an integer with Indonesian thousands separators."""
    return f"{int(value):,}".replace(",", ".")


@register.filter
def signed_intcomma_id(value):
    """Format a signed point amount using a typographic minus sign."""
    points = int(value)
    sign = "+" if points >= 0 else "−"
    return f"{sign}{intcomma_id(abs(points))}"


@register.filter
def id_short_date(value):
    """Format a date using the abbreviated Indonesian month name."""
    local_date = timezone.localtime(value) if timezone.is_aware(value) else value
    month = MONTH_ABBREVIATIONS[local_date.month - 1]
    return f"{local_date.day:02d} {month} {local_date.year}"
