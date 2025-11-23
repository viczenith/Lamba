# Dynamic Slug-Based URL Routing
# Replaces static routes with company-scoped routes
# 
# Pattern:
#   Static:  /admin-dashboard
#   Dynamic: /{company-slug}/dashboard
#   Example: /victor-godwin-ventures/dashboard
#
# This file shows how to update estateApp/urls.py with dynamic slug routing

from django.urls import path, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.views import LogoutView, PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
from .views import *
from .dynamic_slug_routing import company_slug_required, company_slug_context, secure_company_slug

# ============================================================================
# RECOMMENDED URL PATTERNS WITH DYNAMIC SLUGS
# ============================================================================

urlpatterns = [
    
    # ========================================================================
    # AUTHENTICATION ROUTES (Slug-Aware)
    # ========================================================================
    
    # Company-specific login
    # URL: /victor-godwin-ventures/login
    path('<slug:company_slug>/login/', company_slug_context(CustomLoginView.as_view()), name='company-login'),
    
    # Global login (fallback)
    path('login/', CustomLoginView.as_view(), name='login'),
    
    # Logout (works globally)
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    
    # Password reset (can add company slug if needed)
    path('password-reset/', PasswordResetView.as_view(template_name='auth/password_reset.html'), name='password_reset'),
    path('password-reset/done/', PasswordResetDoneView.as_view(template_name='auth/password_reset_done.html'), name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/', PasswordResetConfirmView.as_view(template_name='auth/password_reset_confirm.html'), name='password_reset_confirm'),
    path('password-reset/complete/', PasswordResetCompleteView.as_view(template_name='auth/password_reset_complete.html'), name='password_reset_complete'),
    
    # Registration (multi-tenant aware)
    path('register/', company_registration, name='register'),
    path('<slug:company_slug>/register/', company_slug_context(company_registration), name='company-register'),
    path('client/register/', client_registration, name='client_register'),
    path('<slug:company_slug>/client/register/', company_slug_context(client_registration), name='company-client-register'),
    path('marketer/register/', marketer_registration, name='marketer_register'),
    path('<slug:company_slug>/marketer/register/', company_slug_context(marketer_registration), name='company-marketer-register'),
    
    # Company profile (global & scoped)
    path('company-profile/', company_profile_view, name='company-profile'),
    path('<slug:company_slug>/company-profile/', company_slug_required(company_profile_view), name='company-profile-scoped'),
    path('company-profile/update/', company_profile_update, name='company-profile-update'),
    path('<slug:company_slug>/company-profile/update/', company_slug_required(company_profile_update), name='company-profile-scoped-update'),
    
    # ========================================================================
    # ADMIN DASHBOARD ROUTES (Slug-Based)
    # ========================================================================
    
    # Main dashboard
    # URL: /victor-godwin-ventures/dashboard
    path('<slug:company_slug>/dashboard/', secure_company_slug(admin_dashboard), name='company-dashboard'),
    
    # Alternative: If you want /victor-godwin-ventures/ to show dashboard
    path('<slug:company_slug>/', secure_company_slug(admin_dashboard), name='company-home'),
    
    # Management dashboard
    path('<slug:company_slug>/management-dashboard/', secure_company_slug(management_dashboard), name='company-management-dashboard'),
    
    # Company-specific home (redirect to dashboard)
    path('', login_required(HomeView.as_view()), name="home"),
    
    # ========================================================================
    # PLOT MANAGEMENT ROUTES (Slug-Based)
    # ========================================================================
    
    # Plot sizes
    path('<slug:company_slug>/plot-sizes/', secure_company_slug(add_plotsize), name='company-plot-sizes'),
    path('<slug:company_slug>/plot-sizes/<int:pk>/delete/', secure_company_slug(delete_plotsize), name='company-delete-plotsize'),
    
    # Plot numbers
    path('<slug:company_slug>/plot-numbers/', secure_company_slug(add_plotnumber), name='company-plot-numbers'),
    path('<slug:company_slug>/plot-numbers/<int:pk>/delete/', secure_company_slug(delete_plotnumber), name='company-delete-plotnumber'),
    
    # Plot allocation
    path('<slug:company_slug>/allocate-plots/', secure_company_slug(plot_allocation), name='company-plot-allocation'),
    path('<slug:company_slug>/plot-data/', secure_company_slug(fetch_plot_data), name='company-fetch-plot-data'),
    path('<slug:company_slug>/plots/load/', secure_company_slug(load_plots), name='company-load-plots'),
    path('<slug:company_slug>/plots/allocated/', secure_company_slug(get_allocated_plots), name='company-get-allocated-plots'),
    
    # ========================================================================
    # ESTATE ROUTES (Slug-Based)
    # ========================================================================
    
    # Estate management
    path('<slug:company_slug>/estates/', secure_company_slug(view_estate), name='company-estates'),
    path('<slug:company_slug>/estates/add/', secure_company_slug(add_estate), name='company-add-estate'),
    path('<slug:company_slug>/estates/<int:estate_id>/', secure_company_slug(view_estate), name='company-view-estate'),
    path('<slug:company_slug>/estates/<int:estate_id>/edit/', secure_company_slug(update_estate), name='company-edit-estate'),
    path('<slug:company_slug>/estates/<int:estate_id>/delete/', secure_company_slug(delete_estate), name='company-delete-estate'),
    
    # Estate plots
    path('<slug:company_slug>/estates/<int:estate_id>/plots/', secure_company_slug(allocated_plot), name='company-estate-plots'),
    path('<slug:company_slug>/estates/<int:estate_id>/plots/add/', secure_company_slug(add_estate_plot), name='company-add-estate-plot'),
    path('<slug:company_slug>/estates/<int:estate_id>/plots/<int:id>/edit/', secure_company_slug(edit_estate_plot), name='company-edit-estate-plot'),
    path('<slug:company_slug>/estates/<int:estate_id>/plot-sizes/', secure_company_slug(get_plot_sizes), name='company-estate-plot-sizes'),
    
    # Estate allocations
    path('<slug:company_slug>/estates/<int:estate_id>/allocations/', secure_company_slug(view_allocated_plot), name='company-estate-allocations'),
    path('<slug:company_slug>/allocate-units/', secure_company_slug(allocate_units), name='company-allocate-units'),
    path('<slug:company_slug>/allocations/update/', secure_company_slug(update_allocated_plot), name='company-update-allocation'),
    path('<slug:company_slug>/allocations/delete/', secure_company_slug(delete_allocation), name='company-delete-allocation'),
    path('<slug:company_slug>/allocations/download/', secure_company_slug(download_allocations), name='company-download-allocations'),
    
    # Estate layouts
    path('<slug:company_slug>/estates/<int:estate_id>/layout/add/', secure_company_slug(add_estate_layout), name='company-add-estate-layout'),
    path('<slug:company_slug>/estates/<int:estate_id>/map/add/', secure_company_slug(add_estate_map), name='company-add-estate-map'),
    path('<slug:company_slug>/estates/<int:estate_id>/floor-plans/', secure_company_slug(add_floor_plan), name='company-add-floor-plan'),
    path('<slug:company_slug>/estates/<int:estate_id>/prototypes/', secure_company_slug(add_prototypes), name='company-add-prototypes'),
    path('<slug:company_slug>/estates/<int:estate_id>/amenities/', secure_company_slug(update_estate_amenities), name='company-update-amenities'),
    
    # ========================================================================
    # CLIENT MANAGEMENT ROUTES (Slug-Based)
    # ========================================================================
    
    path('<slug:company_slug>/clients/', secure_company_slug(client), name='company-clients'),
    path('<slug:company_slug>/clients/<int:pk>/', secure_company_slug(client_profile), name='company-client-profile'),
    path('<slug:company_slug>/clients/<int:pk>/soft-delete/', secure_company_slug(client_soft_delete), name='company-client-soft-delete'),
    path('<slug:company_slug>/clients/<int:pk>/restore/', secure_company_slug(client_restore), name='company-client-restore'),
    
    # ========================================================================
    # MARKETER MANAGEMENT ROUTES (Slug-Based)
    # ========================================================================
    
    path('<slug:company_slug>/marketers/', secure_company_slug(marketer_list), name='company-marketers'),
    path('<slug:company_slug>/marketers/<int:pk>/', secure_company_slug(admin_marketer_profile), name='company-marketer-profile'),
    path('<slug:company_slug>/marketers/<int:pk>/soft-delete/', secure_company_slug(marketer_soft_delete), name='company-marketer-soft-delete'),
    path('<slug:company_slug>/marketers/<int:pk>/restore/', secure_company_slug(marketer_restore), name='company-marketer-restore'),
    path('<slug:company_slug>/marketer-performance/', secure_company_slug(MarketerPerformanceView.as_view()), name='company-marketer-performance'),
    
    # ========================================================================
    # TRANSACTION & BILLING ROUTES (Slug-Based)
    # ========================================================================
    
    path('<slug:company_slug>/transactions/', secure_company_slug(add_transaction), name='company-transactions'),
    path('<slug:company_slug>/transactions/add/', secure_company_slug(add_transaction), name='company-add-transaction'),
    path('<slug:company_slug>/transactions/<int:transaction_id>/details/', secure_company_slug(ajax_transaction_details), name='company-transaction-details'),
    path('<slug:company_slug>/payment-history/', secure_company_slug(ajax_payment_history), name='company-payment-history'),
    path('<slug:company_slug>/receipt/<int:transaction_id>/', secure_company_slug(generate_receipt_pdf), name='company-generate-receipt'),
    path('<slug:company_slug>/payment/receipt/<str:reference_code>/', secure_company_slug(payment_receipt), name='company-payment-receipt'),
    
    # ========================================================================
    # PROMOTION & PRICING ROUTES (Slug-Based)
    # ========================================================================
    
    path('<slug:company_slug>/promotions/', secure_company_slug(PromotionListView.as_view()), name='company-promotions'),
    path('<slug:company_slug>/promotions/<int:pk>/', secure_company_slug(PromotionDetailView.as_view()), name='company-promotion-detail'),
    path('<slug:company_slug>/property-prices/', secure_company_slug(property_price_add), name='company-property-prices'),
    path('<slug:company_slug>/property-prices/<int:pk>/edit/', secure_company_slug(property_price_edit), name='company-edit-property-price'),
    path('<slug:company_slug>/property-prices/<int:pk>/history/', secure_company_slug(property_price_history), name='company-property-price-history'),
    
    # ========================================================================
    # CHAT & MESSAGING ROUTES (Slug-Based)
    # ========================================================================
    
    path('<slug:company_slug>/chat/', secure_company_slug(chat_view), name='company-chat'),
    path('<slug:company_slug>/chat/<int:client_id>/', secure_company_slug(admin_chat_view), name='company-admin-chat'),
    path('<slug:company_slug>/chat/marketer/<int:marketer_id>/', secure_company_slug(admin_marketer_chat_view), name='company-admin-marketer-chat'),
    path('<slug:company_slug>/chat/clients/', secure_company_slug(admin_client_chat_list), name='company-client-chat-list'),
    path('<slug:company_slug>/chat/delete/<int:message_id>/', secure_company_slug(delete_message), name='company-delete-message'),
    
    # ========================================================================
    # USER PROFILES (Slug-Based)
    # ========================================================================
    
    path('<slug:company_slug>/profile/', secure_company_slug(user_profile), name='company-user-profile'),
    path('<slug:company_slug>/profile/<int:pk>/', secure_company_slug(client_profile), name='company-profile-view'),
    path('<slug:company_slug>/admin-profile/', secure_company_slug(admin_toggle_mute), name='company-admin-toggle-mute'),
    path('<slug:company_slug>/admin-profile/<int:user_id>/delete/', secure_company_slug(admin_delete_admin), name='company-admin-delete-admin'),
    
    # ========================================================================
    # NOTIFICATIONS (Slug-Based)
    # ========================================================================
    
    path('<slug:company_slug>/notifications/', secure_company_slug(notifications_all), name='company-notifications'),
    path('<slug:company_slug>/notifications/<int:un_id>/', secure_company_slug(notification_detail), name='company-notification-detail'),
    path('<slug:company_slug>/notifications/<int:un_id>/mark-read/', secure_company_slug(mark_notification_read), name='company-mark-notification-read'),
    path('<slug:company_slug>/announcements/send/', secure_company_slug(send_announcement), name='company-send-announcement'),
    
    # ========================================================================
    # API ROUTES (Slug-Based for Multi-Tenant)
    # ========================================================================
    
    path('<slug:company_slug>/api/plot-sizes/', secure_company_slug(get_plot_sizes), name='company-api-plot-sizes'),
    path('<slug:company_slug>/api/estate/<int:estate_id>/plot-sizes/', secure_company_slug(estate_plot_sizes), name='company-api-estate-plot-sizes'),
    path('<slug:company_slug>/api/clients/search/', secure_company_slug(search_clients_api), name='company-api-search-clients'),
    path('<slug:company_slug>/api/marketers/search/', secure_company_slug(search_marketers_api), name='company-api-search-marketers'),
    path('<slug:company_slug>/api/estate-details/<int:estate_id>/', secure_company_slug(get_estate_details), name='company-api-estate-details'),
    path('<slug:company_slug>/api/price-update/<int:pk>/', secure_company_slug(price_update_json), name='company-api-price-update'),
    
    # ========================================================================
    # LEGACY ROUTES (Backward Compatibility - Without Slug)
    # ========================================================================
    # Keep old routes working for backward compatibility
    # These will redirect to new slug-based routes if authenticated user has company
    
    path('admin_dashboard/', admin_dashboard, name="admin-dashboard"),
    path('management-dashboard/', management_dashboard, name='management-dashboard'),
    path('client/', client, name="client"),
    path('marketer-list/', marketer_list, name="marketer-list"),
    path('client-dashboard/', client_dashboard, name="client-dashboard"),
    path('marketer-dashboard/', marketer_dashboard, name="marketer-dashboard"),
    path('marketer-profile/', marketer_profile, name="marketer-profile"),
    
    # ========================================================================
    # SPECIAL ROUTES
    # ========================================================================
    
    # 404 handler for invalid slugs
    path('<slug:company_slug>/', secure_company_slug(admin_dashboard), name='company-root'),
    
]

# Static and media files
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
