# -*- coding: utf-8 -*-
"""
Script to add company isolation to property price and promo views
"""

with open('estateApp/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

changes_made = []

# 1. Fix estate_plot_sizes - add company isolation
old_text1 = '''@require_http_methods(["GET"])
@login_required
@user_passes_test(is_admin)
def estate_plot_sizes(request, estate_id):
    estate = get_object_or_404(Estate, pk=estate_id)
    units = PlotSizeUnits.objects.filter(estate_plot__estate=estate).select_related('plot_size')'''

new_text1 = '''@require_http_methods(["GET"])
@login_required
@user_passes_test(is_admin)
def estate_plot_sizes(request, estate_id):
    # Company isolation - ensure estate belongs to user's company
    user_company = getattr(request.user, 'company_profile', None)
    if not user_company:
        return JsonResponse({'error': 'No company access'}, status=403)
    
    estate = get_object_or_404(Estate, pk=estate_id, company=user_company)
    units = PlotSizeUnits.objects.filter(estate_plot__estate=estate).select_related('plot_size')'''

if old_text1 in content:
    content = content.replace(old_text1, new_text1)
    changes_made.append('estate_plot_sizes')

# 2. Fix estate_bulk_price_data - add company isolation  
old_text2 = '''@login_required
@user_passes_test(is_admin)
def estate_bulk_price_data(request, estate_id):
    """
    Returns estate info with all plot units and their current prices for bulk updating.
    """
    estate = get_object_or_404(Estate, pk=estate_id)'''

new_text2 = '''@login_required
@user_passes_test(is_admin)
def estate_bulk_price_data(request, estate_id):
    """
    Returns estate info with all plot units and their current prices for bulk updating.
    Company-isolated for multi-tenant security.
    """
    # Company isolation - ensure estate belongs to user's company
    user_company = getattr(request.user, 'company_profile', None)
    if not user_company:
        return JsonResponse({'error': 'No company access'}, status=403)
    
    estate = get_object_or_404(Estate, pk=estate_id, company=user_company)'''

if old_text2 in content:
    content = content.replace(old_text2, new_text2)
    changes_made.append('estate_bulk_price_data')

# 3. Fix property_price_bulk_update - add company isolation
old_text3 = '''@csrf_exempt
@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def property_price_bulk_update(request):
    """
    Bulk update property prices for multiple plot units.
    """
    try:
        payload = json.loads(request.body)
        estate_id = payload["estate_id"]
        effective = payload["effective"]
        notes = payload.get("notes", "")
        notify = payload.get("notify", False)
        updates = payload["updates"]  # List of {plot_unit_id, new_price}
        
        estate = Estate.objects.get(pk=estate_id)
    except (KeyError, Estate.DoesNotExist, json.JSONDecodeError, ValueError) as e:
        return JsonResponse({"status": "error", "message": f"Invalid payload: {str(e)}"}, status=400)'''

new_text3 = '''@csrf_exempt
@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def property_price_bulk_update(request):
    """
    Bulk update property prices for multiple plot units.
    Company-isolated for multi-tenant security.
    """
    # Company isolation - get user's company
    user_company = getattr(request.user, 'company_profile', None)
    if not user_company:
        return JsonResponse({'error': 'No company access'}, status=403)
    
    try:
        payload = json.loads(request.body)
        estate_id = payload["estate_id"]
        effective = payload["effective"]
        notes = payload.get("notes", "")
        notify = payload.get("notify", False)
        updates = payload["updates"]  # List of {plot_unit_id, new_price}
        
        # Company isolation - ensure estate belongs to user's company
        estate = Estate.objects.get(pk=estate_id, company=user_company)
    except (KeyError, Estate.DoesNotExist, json.JSONDecodeError, ValueError) as e:
        return JsonResponse({"status": "error", "message": f"Invalid payload: {str(e)}"}, status=400)'''

if old_text3 in content:
    content = content.replace(old_text3, new_text3)
    changes_made.append('property_price_bulk_update')

# 4. Fix property_price_add - add company isolation
old_text4 = '''@csrf_exempt
@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def property_price_add(request):
    try:
        payload = json.loads(request.body)
        estate_id = payload["estate_id"]
        plot_unit_id = payload["plot_unit_id"]
        presale = Decimal(payload["presale"])
        effective = payload["effective"]
        notes = payload.get("notes", "")
        
        estate = Estate.objects.get(pk=estate_id)
        unit = PlotSizeUnits.objects.get(pk=plot_unit_id)

    except (KeyError, Estate.DoesNotExist, PlotSizeUnits.DoesNotExist, 
            ValueError, json.JSONDecodeError) as e:
        return HttpResponseBadRequest("Invalid payload")'''

new_text4 = '''@csrf_exempt
@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def property_price_add(request):
    # Company isolation - get user's company
    user_company = getattr(request.user, 'company_profile', None)
    if not user_company:
        return JsonResponse({'error': 'No company access'}, status=403)
    
    try:
        payload = json.loads(request.body)
        estate_id = payload["estate_id"]
        plot_unit_id = payload["plot_unit_id"]
        presale = Decimal(payload["presale"])
        effective = payload["effective"]
        notes = payload.get("notes", "")
        
        # Company isolation - ensure estate belongs to user's company
        estate = Estate.objects.get(pk=estate_id, company=user_company)
        unit = PlotSizeUnits.objects.get(pk=plot_unit_id, estate_plot__estate__company=user_company)

    except (KeyError, Estate.DoesNotExist, PlotSizeUnits.DoesNotExist, 
            ValueError, json.JSONDecodeError) as e:
        return HttpResponseBadRequest("Invalid payload")'''

if old_text4 in content:
    content = content.replace(old_text4, new_text4)
    changes_made.append('property_price_add')

# 5. Fix property_price_edit - add company isolation
old_text5 = '''@csrf_exempt
@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST", "PUT"])
def property_price_edit(request, pk):
    """
    Updates an existing PropertyPrice (only current/effective/notes)
    and appends a PriceHistory entry using the unchanged presale.
    Optionally sends notifications to clients and marketers.
    """
    pp = get_object_or_404(PropertyPrice, pk=pk)'''

new_text5 = '''@csrf_exempt
@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST", "PUT"])
def property_price_edit(request, pk):
    """
    Updates an existing PropertyPrice (only current/effective/notes)
    and appends a PriceHistory entry using the unchanged presale.
    Optionally sends notifications to clients and marketers.
    Company-isolated for multi-tenant security.
    """
    # Company isolation - ensure property price belongs to user's company
    user_company = getattr(request.user, 'company_profile', None)
    if not user_company:
        return JsonResponse({'error': 'No company access'}, status=403)
    
    pp = get_object_or_404(PropertyPrice, pk=pk, estate__company=user_company)'''

if old_text5 in content:
    content = content.replace(old_text5, new_text5)
    changes_made.append('property_price_edit')

# 6. Fix promo_create - add company isolation
old_text6 = '''@csrf_exempt
@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
@csrf_exempt
@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def promo_create(request):
    try:
        data = json.loads(request.body)

        name = data.get("name", "").strip()
        discount = float(data.get("discount", 0))
        start = parse_date(data.get("start"))
        end = parse_date(data.get("end"))
        description = data.get("description", "")
        estate_ids = data.get("estates", [])

        if not name or not start or not end or not estate_ids:
            return JsonResponse({"status": "error", "message": "Missing required fields."}, status=400)

        promo = PromotionalOffer.objects.create(
            name=name, discount=discount,
            start=start, end=end, description=description
        )
        promo.estates.set(Estate.objects.filter(id__in=estate_ids))'''

new_text6 = '''@csrf_exempt
@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def promo_create(request):
    # Company isolation - get user's company
    user_company = getattr(request.user, 'company_profile', None)
    if not user_company:
        return JsonResponse({'error': 'No company access'}, status=403)
    
    try:
        data = json.loads(request.body)

        name = data.get("name", "").strip()
        discount = float(data.get("discount", 0))
        start = parse_date(data.get("start"))
        end = parse_date(data.get("end"))
        description = data.get("description", "")
        estate_ids = data.get("estates", [])

        if not name or not start or not end or not estate_ids:
            return JsonResponse({"status": "error", "message": "Missing required fields."}, status=400)

        promo = PromotionalOffer.objects.create(
            name=name, discount=discount,
            start=start, end=end, description=description,
            company=user_company  # Company isolation
        )
        # Company isolation - only set estates that belong to user's company
        promo.estates.set(Estate.objects.filter(id__in=estate_ids, company=user_company))'''

if old_text6 in content:
    content = content.replace(old_text6, new_text6)
    changes_made.append('promo_create')

# 7. Fix promo_update - add company isolation
old_text7 = '''@csrf_exempt
@login_required
@user_passes_test(is_admin)
@require_http_methods(["PUT"])
def promo_update(request, promo_id):
    try:
        data = json.loads(request.body)
        promo = get_object_or_404(PromotionalOffer, id=promo_id)

        promo.name = data.get("name", promo.name).strip()
        promo.discount = float(data.get("discount", promo.discount))
        promo.start = parse_date(data.get("start")) or promo.start
        promo.end = parse_date(data.get("end")) or promo.end
        promo.description = data.get("description", promo.description)
        estate_ids = data.get("estates", [])

        if not promo.name or not promo.start or not promo.end or not estate_ids:
            return JsonResponse({"status": "error", "message": "Missing required fields."}, status=400)

        promo.save()
        promo.estates.set(Estate.objects.filter(id__in=estate_ids))'''

new_text7 = '''@csrf_exempt
@login_required
@user_passes_test(is_admin)
@require_http_methods(["PUT"])
def promo_update(request, promo_id):
    # Company isolation - get user's company
    user_company = getattr(request.user, 'company_profile', None)
    if not user_company:
        return JsonResponse({'error': 'No company access'}, status=403)
    
    try:
        data = json.loads(request.body)
        # Company isolation - ensure promo belongs to user's company
        promo = get_object_or_404(PromotionalOffer, id=promo_id, company=user_company)

        promo.name = data.get("name", promo.name).strip()
        promo.discount = float(data.get("discount", promo.discount))
        promo.start = parse_date(data.get("start")) or promo.start
        promo.end = parse_date(data.get("end")) or promo.end
        promo.description = data.get("description", promo.description)
        estate_ids = data.get("estates", [])

        if not promo.name or not promo.start or not promo.end or not estate_ids:
            return JsonResponse({"status": "error", "message": "Missing required fields."}, status=400)

        promo.save()
        # Company isolation - only set estates that belong to user's company
        promo.estates.set(Estate.objects.filter(id__in=estate_ids, company=user_company))'''

if old_text7 in content:
    content = content.replace(old_text7, new_text7)
    changes_made.append('promo_update')

# Write the updated content
with open('estateApp/views.py', 'w', encoding='utf-8') as f:
    f.write(content)

print(f'Successfully updated {len(changes_made)} functions:')
for change in changes_made:
    print(f'  - {change}')
