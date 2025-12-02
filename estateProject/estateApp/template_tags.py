# estateApp/template_tags.py
"""
Django template tags and filters for profile URL generation and company isolation.
Usage in templates: {% load profile_tags %}
"""

from django import template
from django.urls import reverse
import re

register = template.Library()


def generate_name_slug(full_name):
    """
    Convert full name to URL-safe slug for profile links.
    Example: "Victor Godwin" -> "victor-godwin"
    """
    if not full_name:
        return None
    
    # Convert to lowercase and replace spaces with hyphens
    slug = full_name.strip().lower().replace(' ', '-')
    # Remove any special characters except hyphens
    slug = re.sub(r'[^a-z0-9\-]', '', slug)
    # Remove multiple consecutive hyphens
    slug = re.sub(r'-+', '-', slug)
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    
    return slug if slug else None


@register.filter
def client_profile_url(client, company=None):
    """
    Generate client profile URL using slug-based routing.
    Usage in template: {{ client|client_profile_url:company }}
    
    Output: /victor-godwin.client-profile?company=lamba-real-homes
    """
    if not client:
        return '#'
    
    # Get slug from client's full_name
    slug = generate_name_slug(client.full_name)
    if not slug:
        return '#'
    
    # Build URL with company parameter
    url = f"/{slug}.client-profile/"
    
    if company:
        company_slug = getattr(company, 'slug', None)
        if company_slug:
            url += f"?company={company_slug}"
    
    return url


@register.filter
def marketer_profile_url(marketer, company=None):
    """
    Generate marketer profile URL using slug-based routing.
    Usage in template: {{ marketer|marketer_profile_url:company }}
    
    Output: /victor-godwin.marketer-profile?company=lamba-real-homes
    """
    if not marketer:
        return '#'
    
    # Get slug from marketer's full_name
    slug = generate_name_slug(marketer.full_name)
    if not slug:
        return '#'
    
    # Build URL with company parameter
    url = f"/{slug}.marketer-profile/"
    
    if company:
        company_slug = getattr(company, 'slug', None)
        if company_slug:
            url += f"?company={company_slug}"
    
    return url


@register.simple_tag
def client_profile_link(client, company=None, css_class=""):
    """
    Generate full HTML link to client profile with security-aware slug routing.
    Usage in template: {% client_profile_link client company "btn btn-primary" %}
    
    Returns: <a href="/victor-godwin.client-profile?company=lamba-real-homes" class="btn btn-primary">Victor Godwin</a>
    """
    if not client:
        return "N/A"
    
    slug = generate_name_slug(client.full_name)
    if not slug:
        return client.full_name
    
    url = f"/{slug}.client-profile/"
    if company:
        company_slug = getattr(company, 'slug', None)
        if company_slug:
            url += f"?company={company_slug}"
    
    css_attr = f' class="{css_class}"' if css_class else ""
    return f'<a href="{url}"{css_attr}>{client.full_name}</a>'


@register.simple_tag
def marketer_profile_link(marketer, company=None, css_class=""):
    """
    Generate full HTML link to marketer profile with security-aware slug routing.
    Usage in template: {% marketer_profile_link marketer company "btn btn-info" %}
    
    Returns: <a href="/victor-godwin.marketer-profile?company=lamba-real-homes" class="btn btn-info">Victor Godwin</a>
    """
    if not marketer:
        return "N/A"
    
    slug = generate_name_slug(marketer.full_name)
    if not slug:
        return marketer.full_name
    
    url = f"/{slug}.marketer-profile/"
    if company:
        company_slug = getattr(company, 'slug', None)
        if company_slug:
            url += f"?company={company_slug}"
    
    css_attr = f' class="{css_class}"' if css_class else ""
    return f'<a href="{url}"{css_attr}>{marketer.full_name}</a>'


@register.filter
def name_slug(full_name):
    """
    Convert full name to URL-safe slug.
    Usage in template: {{ user.full_name|name_slug }}
    
    Output: victor-godwin
    """
    return generate_name_slug(full_name)
