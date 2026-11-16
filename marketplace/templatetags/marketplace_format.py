from django import template

register = template.Library()


@register.filter
def intcomma_id(value):
    """Format an integer with Indonesian dot thousand separators."""
    try:
        return f"{int(value):,}".replace(",", ".")
    except (TypeError, ValueError):
        return value


@register.filter
def rupiah(value):
    """Format an integer amount as 'Rp 185.000'."""
    try:
        return f"Rp {int(value):,}".replace(",", ".")
    except (TypeError, ValueError):
        return f"Rp {value}"

