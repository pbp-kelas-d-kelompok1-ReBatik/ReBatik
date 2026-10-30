"""Template filters for displaying upcycling prices."""

from decimal import Decimal

from django import template

register = template.Library()


@register.filter
def rupiah(value):
    """Format a rupiah amount with Indonesian thousands separators."""
    amount = Decimal(str(value or 0))
    return f"{int(amount):,}".replace(",", ".")
