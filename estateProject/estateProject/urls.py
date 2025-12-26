from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns


from adminSupport import views as admin_support_views
from . import error_handlers

urlpatterns = [
    # Django Admin
    path('admin/', admin.site.urls),
    
    # Super Admin - Master Tenant Management
    path('super-admin/', include('superAdmin.urls', namespace='superadmin')),
    
    # Main App
    path('', include('estateApp.urls')),
    
    # Admin Support
    path('admin-support/', include(('adminSupport.urls', 'adminsupport'), namespace='adminsupport')),
    path('api/admin-support/client-chats/', admin_support_views.chat_list_clients_api, name='adminsupport_client_chats'),
    path('api/admin-support/marketer-chats/', admin_support_views.chat_list_marketers_api, name='adminsupport_marketer_chats'),
    path('api/admin-support/chat/search/clients/', admin_support_views.chat_search_clients, name='adminsupport_chat_search_clients'),
    path('api/admin-support/chat/search/marketers/', admin_support_views.chat_search_marketers, name='adminsupport_chat_search_marketers'),
    path('api/admin-support/birthdays/summary/', admin_support_views.api_birthdays_summary, name='adminsupport_birthdays_summary'),
    path('api/admin-support/birthdays/counts/', admin_support_views.api_birthdays_counts, name='adminsupport_birthdays_counts'),
    path('api/admin-support/special-days/summary/', admin_support_views.api_special_days_summary, name='adminsupport_special_days_summary'),
    path('api/admin-support/special-days/counts/', admin_support_views.api_special_days_counts, name='adminsupport_special_days_counts'),
    path('api/admin-support/custom-special-days/', admin_support_views.api_custom_special_days, name='adminsupport_custom_special_days'),
    path('api/admin-support/custom-special-days/<uuid:day_id>/', admin_support_views.api_custom_special_day_detail, name='adminsupport_custom_special_day_detail'),
    
    # API Routes
    path('api/', include('DRF.company_admin.api_urls.api_urls')),
    path('api/', include('DRF.urls', namespace='drf')),
]

# Static and media files
urlpatterns += staticfiles_urlpatterns()

if settings.DEBUG or settings.MEDIA_URL:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Custom error handlers
handler400 = 'estateProject.error_handlers.custom_400'
handler401 = 'estateProject.error_handlers.custom_401'
handler403 = 'estateProject.error_handlers.custom_403'
handler404 = 'estateProject.error_handlers.custom_404'
handler405 = 'estateProject.error_handlers.custom_405'
handler408 = 'estateProject.error_handlers.custom_408'
handler410 = 'estateProject.error_handlers.custom_410'
handler429 = 'estateProject.error_handlers.custom_429'
handler451 = 'estateProject.error_handlers.custom_451'
handler500 = 'estateProject.error_handlers.custom_500'
handler502 = 'estateProject.error_handlers.custom_502'
handler503 = 'estateProject.error_handlers.custom_503'

