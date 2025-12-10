from django import template
from django.utils import timezone
from datetime import timedelta
import os
register = template.Library()
from django.conf import settings
from django.templatetags.static import static
from django.contrib.staticfiles import finders

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)




@register.filter
def is_allocated_in_estate(number, estate_id):
    if hasattr(number, 'allocated_estate_id'):
        return number.allocated_estate_id == estate_id
    return False


@register.filter
def endswith(value, arg):
    if isinstance(value, str):
        return value.endswith(arg)
    return False


@register.filter
def filename(value):
    if not value:
        return ''
    # Ensure robust handling of both POSIX and Windows-style paths
    return os.path.basename(str(value))


@register.filter
def sub(value, arg):
    return value - arg


@register.filter
def within_minutes(value, minutes=30):
    try:
        dt = timezone.make_aware(value) if timezone.is_naive(value) else value
    except Exception:
        return False
    return timezone.now() - dt <= timedelta(minutes=minutes)


@register.filter
def isoformat(value):
    try:
        return value.isoformat()
    except Exception:
        return ""


@register.filter
def versioned_static(path):
    """Return the static URL for `path` with a cache-busting mtime query param when possible."""
    try:
        url = static(path)
        abs_path = finders.find(path)
        if abs_path and os.path.exists(abs_path):
            mtime = int(os.path.getmtime(abs_path))
            return f"{url}?v={mtime}"
        return url
    except Exception:
        return static(path)


@register.filter
def versioned_file(file_obj):
    """Return the file URL with a cache-busting mtime query param for FileField-like objects.
    If passed a string URL, return as-is.
    """
    try:
        # FileField or ImageField
        if hasattr(file_obj, 'url') and hasattr(file_obj, 'name'):
            url = file_obj.url
            name = file_obj.name
            abs_path = os.path.join(settings.MEDIA_ROOT or '', name)
            if abs_path and os.path.exists(abs_path):
                mtime = int(os.path.getmtime(abs_path))
                return f"{url}?v={mtime}"
            return url
        # If a raw URL string is passed, just return it
        return str(file_obj)
    except Exception:
        try:
            return getattr(file_obj, 'url', '')
        except Exception:
            return ''


@register.filter
def sum_attribute(queryset, attribute):
    """Sum up a specific attribute from a list of objects or dictionaries."""
    try:
        total = 0
        for item in queryset:
            # Handle both dictionary and object attribute access
            if isinstance(item, dict):
                value = item.get(attribute, 0)
            else:
                value = getattr(item, attribute, 0)
            
            # Add to total, treating None as 0
            total += value if value is not None else 0
        return total
    except Exception:
        return 0


@register.filter
def target_status(achievement):
    """
    Returns target status text based on achievement percentage.
    Target Logic:
    - Below Target: 0% to 49% achievement
    - On Target: 50% to 100% achievement  
    - Above Target: 101%+ achievement
    Examples: "Below Target (14%)", "On Target (75%)", "25% Above Target"
    """
    try:
        if achievement is None:
            return "No Target Set"
        
        achievement = float(achievement)
        
        if achievement > 100:
            above = int(achievement - 100)
            return f"{above}% Above Target"
        elif achievement >= 50:
            return f"On Target ({int(achievement)}%)"
        else:
            return f"Below Target ({int(achievement)}%)"
    except (ValueError, TypeError):
        return "No Target Set"


@register.filter
def target_status_class(achievement):
    """
    Returns CSS class for target status badge styling.
    Target Logic:
    - Below Target: 0% to 49% achievement (status-below)
    - On Target: 50% to 100% achievement (status-on-track)  
    - Above Target: 101%+ achievement (status-above)
    """
    try:
        if achievement is None:
            return "status-no-target"
        
        achievement = float(achievement)
        
        if achievement > 100:
            return "status-above"
        elif achievement >= 50:
            return "status-on-track"
        else:
            return "status-below"
    except (ValueError, TypeError):
        return "status-no-target"
