# -*- coding: utf-8 -*-
"""
Script to add company isolation to remaining property price views
"""

with open('estateApp/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

changes_made = []

# 1. Fix property_price_prefill - add company isolation
old_text1 = '''@login_required
@require_GET
def property_price_prefill(request):
    estate_id = request.GET.get('estate')
    plot_unit_id = request.GET.get('plot_unit')
    try:
        pp = PropertyPrice.objects.get(estate_id=estate_id, plot_unit_id=plot_unit_id)'''

new_text1 = '''@login_required
@require_GET
def property_price_prefill(request):
    # Company isolation - get user's company
    user_company = getattr(request.user, 'company_profile', None)
    if not user_company:
        return JsonResponse({'error': 'No company access'}, status=403)
    
    estate_id = request.GET.get('estate')
    plot_unit_id = request.GET.get('plot_unit')
    try:
        # Company isolation - ensure property price belongs to user's company
        pp = PropertyPrice.objects.get(estate_id=estate_id, plot_unit_id=plot_unit_id, estate__company=user_company)'''

if old_text1 in content:
    content = content.replace(old_text1, new_text1)
    changes_made.append('property_price_prefill')

# 2. Fix property_price_history - add company isolation
old_text2 = '''@login_required
@user_passes_test(is_admin)
@require_GET
def property_price_history(request, pk):
    pp = get_object_or_404(PropertyPrice, pk=pk)
    history = []'''

new_text2 = '''@login_required
@user_passes_test(is_admin)
@require_GET
def property_price_history(request, pk):
    # Company isolation - ensure property price belongs to user's company
    user_company = getattr(request.user, 'company_profile', None)
    if not user_company:
        return JsonResponse({'error': 'No company access'}, status=403)
    
    pp = get_object_or_404(PropertyPrice, pk=pk, estate__company=user_company)
    history = []'''

if old_text2 in content:
    content = content.replace(old_text2, new_text2)
    changes_made.append('property_price_history')

# 3. Fix property_price_detail - add company isolation
old_text3 = '''@login_required
@user_passes_test(is_admin)
@require_GET
def property_price_detail(request, pk):
    """
    Returns JSON detail of a PropertyPrice including an active promo adjustment.
    """
    pp = get_object_or_404(PropertyPrice, pk=pk)'''

new_text3 = '''@login_required
@user_passes_test(is_admin)
@require_GET
def property_price_detail(request, pk):
    """
    Returns JSON detail of a PropertyPrice including an active promo adjustment.
    Company-isolated for multi-tenant security.
    """
    # Company isolation - ensure property price belongs to user's company
    user_company = getattr(request.user, 'company_profile', None)
    if not user_company:
        return JsonResponse({'error': 'No company access'}, status=403)
    
    pp = get_object_or_404(PropertyPrice, pk=pk, estate__company=user_company)'''

if old_text3 in content:
    content = content.replace(old_text3, new_text3)
    changes_made.append('property_price_detail')

# 4. Fix get_active_promo_for_estate - add company isolation
old_text4 = '''@require_GET
@login_required
@user_passes_test(is_admin)
def get_active_promo_for_estate(request, estate_id):
    try:'''

new_text4 = '''@require_GET
@login_required
@user_passes_test(is_admin)
def get_active_promo_for_estate(request, estate_id):
    # Company isolation - get user's company
    user_company = getattr(request.user, 'company_profile', None)
    if not user_company:
        return JsonResponse({'error': 'No company access'}, status=403)
    
    try:
        # Company isolation - ensure estate belongs to user's company
        estate = Estate.objects.get(pk=estate_id, company=user_company)'''

if old_text4 in content:
    content = content.replace(old_text4, new_text4)
    changes_made.append('get_active_promo_for_estate')

# Write the updated content
with open('estateApp/views.py', 'w', encoding='utf-8') as f:
    f.write(content)

print(f'Successfully updated {len(changes_made)} functions:')
for change in changes_made:
    print(f'  - {change}')
