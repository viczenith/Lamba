"""
Template tags for personalized URLs
"""
from django import template
from django.urls import reverse

register = template.Library()

@register.simple_tag(takes_context=True)
def personalized_url(context, view_name, *args, **kwargs):
    """
    Generate a personalized URL with user slug prefix.
    Usage: {% personalized_url 'admin-dashboard' %}
    Result: /victor.godwin/admin-dashboard/
    """
    request = context.get('request')
    if not request or not hasattr(request, 'user'):
        return reverse(view_name, args=args, kwargs=kwargs)
    
    user = request.user
    if not user.is_authenticated or not hasattr(user, 'slug') or not user.slug:
        return reverse(view_name, args=args, kwargs=kwargs)
    
    # Map generic view names to personalized view names
    personalized_views = {
        'admin-dashboard': 'personalized-admin-dashboard',
        'management-dashboard': 'personalized-management-dashboard',
        'user-registration': 'personalized-user-registration',
        'marketer-list': 'personalized-marketer-list',
        'client': 'personalized-client-list',
        'plot-allocation': 'personalized-plot-allocation',
        'add-estate': 'personalized-add-estate',
        'view-estate': 'personalized-view-estate',
        'add-estate-plot': 'personalized-add-estate-plot',
        'add-plotsize': 'personalized-add-plotsize',
        'add-plotnumber': 'personalized-add-plotnumber',
        'admin-client-chat-list': 'personalized-admin-client-chat-list',
        
        'marketer-dashboard': 'personalized-marketer-dashboard',
        'marketer-profile': 'personalized-marketer-profile',
        'client-records': 'personalized-client-records',
        'marketer-company-directory': 'personalized-marketer-company-directory',
        'marketer-company-chat': 'personalized-marketer-company-chat',
        
        'client-dashboard': 'personalized-client-dashboard',
        'my-client-profile': 'personalized-my-client-profile',
        'client-records': 'personalized-client-records',
        'client-company-directory': 'personalized-client-company-directory',
        'client-company-chat': 'personalized-client-company-chat',
        'property-list': 'personalized-property-list',
        'client-company-properties': 'personalized-client-company-properties',
        
        'notifications_all': 'personalized-notifications-all',
    }
    
    personalized_view = personalized_views.get(view_name)
    if personalized_view:
        # Add user_slug to kwargs
        kwargs['user_slug'] = user.slug
        return reverse(personalized_view, args=args, kwargs=kwargs)
    
    # Fallback to regular URL
    return reverse(view_name, args=args, kwargs=kwargs)


@register.simple_tag(takes_context=True)
def user_url_prefix(context):
    """
    Get the user's URL prefix (slug).
    Usage: {% user_url_prefix %}
    Result: victor.godwin
    """
    request = context.get('request')
    if not request or not hasattr(request, 'user'):
        return ''
    
    user = request.user
    if not user.is_authenticated or not hasattr(user, 'slug') or not user.slug:
        return ''
    
    return user.slug
