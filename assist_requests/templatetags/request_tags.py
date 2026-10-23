from django import template

register = template.Library()


@register.filter(name='split')
def split(value, arg):
    """Split a string by the given delimiter."""
    return [s.strip() for s in value.split(arg) if s.strip()]


@register.filter(name='strip')
def strip_filter(value):
    """Strip whitespace from a string."""
    return value.strip()
