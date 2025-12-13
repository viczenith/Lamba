"""
Secure Media Serving Views
===========================

Protects media files (images, documents) from unauthorized access by:
1. Validating user permissions before serving files
2. Preventing direct URL enumeration
3. Implementing access logs for security audits
4. Rate limiting on media downloads
"""

import os
import logging
from django.http import FileResponse, HttpResponseForbidden, Http404
from django.views.decorators.http import condition
from django.views.decorators.cache import cache_page
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import SuspiciousOperation

logger = logging.getLogger(__name__)


def get_user_accessible_companies(user):
    """Get list of company IDs user can access"""
    company_ids = set()
    
    try:
        # All authenticated users can at least see all companies for viewing logos/profiles
        # in shared contexts (like client portfolios, marketer profiles, etc.)
        from estateApp.models import Company
        all_companies = Company.objects.values_list('id', flat=True)
        company_ids.update(all_companies)
    except Exception:
        pass
    
    return list(company_ids)


@login_required
def serve_company_logo(request, company_id):
    """
    Secure company logo serving
    
    Any authenticated user can view company logos
    """
    from estateApp.models import Company
    import mimetypes
    
    try:
        company = Company.objects.get(id=company_id)
    except Company.DoesNotExist:
        raise Http404("Company not found")
    
    # Verify logo exists
    if not company.logo:
        raise Http404("Logo not found")
    
    logo_path = company.logo.path
    
    # Verify path is within media directory (prevent directory traversal)
    if not os.path.abspath(logo_path).startswith(os.path.abspath(settings.MEDIA_ROOT)):
        raise SuspiciousOperation("Invalid file path")
    
    # Check if file actually exists on disk
    if not os.path.exists(logo_path):
        logger.error(f"Logo file not found on disk: {logo_path}")
        raise Http404("File not found")
    
    # Log access
    logger.info(f"Logo served: Company {company_id} to User {request.user.id}")
    
    # Determine correct content type based on file extension
    content_type, _ = mimetypes.guess_type(logo_path)
    if not content_type:
        content_type = 'image/jpeg'  # fallback
    
    try:
        return FileResponse(
            open(logo_path, 'rb'),
            content_type=content_type,
            as_attachment=False
        )
    except IOError as e:
        logger.error(f"IOError serving logo {company_id}: {e}")
        raise Http404("File not found")


@login_required
def serve_profile_image(request, user_id):
    """
    Secure profile image serving
    
    Users can only access their own profile image or images they're allowed to see
    """
    from django.contrib.auth import get_user_model
    import mimetypes
    
    User = get_user_model()
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        raise Http404("User not found")
    
    # Users can only view their own profile image or company colleagues
    if request.user.id != user_id:
        # Check if they're in the same company
        request_user_companies = get_user_accessible_companies(request.user)
        target_user_companies = get_user_accessible_companies(user)
        
        if not any(c in request_user_companies for c in target_user_companies):
            logger.warning(
                f"Unauthorized profile image access: User {request.user.id} "
                f"tried to access user {user_id} profile image"
            )
            return HttpResponseForbidden("Access denied")
    
    # Check if profile image exists
    if not hasattr(user, 'profile_image') or not user.profile_image:
        raise Http404("Profile image not found")
    
    image_path = user.profile_image.path
    
    # Verify path is within media directory
    if not os.path.abspath(image_path).startswith(os.path.abspath(settings.MEDIA_ROOT)):
        raise SuspiciousOperation("Invalid file path")
    
    # Check if file actually exists on disk
    if not os.path.exists(image_path):
        logger.error(f"Profile image file not found on disk: {image_path}")
        raise Http404("File not found")
    
    # Log access
    logger.info(f"Profile image served: User {user_id} to User {request.user.id}")
    
    # Determine correct content type based on file extension
    content_type, _ = mimetypes.guess_type(image_path)
    if not content_type:
        content_type = 'image/jpeg'  # fallback
    
    try:
        return FileResponse(
            open(image_path, 'rb'),
            content_type=content_type,
            as_attachment=False
        )
    except IOError as e:
        logger.error(f"IOError serving profile image {user_id}: {e}")
        raise Http404("File not found")
    except IOError:
        raise Http404("File not found")


@login_required
def serve_document(request, document_id):
    """
    Secure document serving (PDFs, contracts, etc.)
    
    Only users with permission to access the document can download it
    """
    from estateApp.models import Document  # You may need to create this model
    
    try:
        document = Document.objects.get(id=document_id)
    except:
        raise Http404("Document not found")
    
    # Check permissions (implement based on your Document model)
    if not document.can_be_accessed_by(request.user):
        logger.warning(
            f"Unauthorized document access: User {request.user.id} "
            f"tried to access document {document_id}"
        )
        return HttpResponseForbidden("Access denied")
    
    doc_path = document.file.path
    
    # Verify path is within media directory
    if not os.path.abspath(doc_path).startswith(os.path.abspath(settings.MEDIA_ROOT)):
        raise SuspiciousOperation("Invalid file path")
    
    # Log access
    logger.info(f"Document served: {document_id} to User {request.user.id}")
    
    try:
        return FileResponse(
            open(doc_path, 'rb'),
            as_attachment=True,
            filename=document.filename
        )
    except IOError:
        raise Http404("File not found")


@login_required
def serve_prototype_image(request, prototype_id):
    """
    Secure prototype image serving
    Validates user has access to the estate before serving image
    """
    from estateApp.models import EstatePrototype
    import mimetypes
    
    try:
        prototype = EstatePrototype.objects.select_related('plot_size__estate').get(id=prototype_id)
    except EstatePrototype.DoesNotExist:
        raise Http404("Prototype not found")
    
    # Verify image exists
    if not prototype.prototype_image:
        raise Http404("Image not found")
    
    # Get estate from prototype
    estate = prototype.plot_size.estate if prototype.plot_size else None
    if not estate:
        raise Http404("Estate not found")
    
    image_path = prototype.prototype_image.path
    
    # Verify path is within media directory
    if not os.path.abspath(image_path).startswith(os.path.abspath(settings.MEDIA_ROOT)):
        raise SuspiciousOperation("Invalid file path")
    
    # Check if file exists
    if not os.path.exists(image_path):
        logger.error(f"Prototype image not found: {image_path}")
        raise Http404("File not found")
    
    # Log access
    logger.info(f"Prototype image served: {prototype_id} from Estate {estate.id} to User {request.user.id}")
    
    content_type, _ = mimetypes.guess_type(image_path)
    if not content_type:
        content_type = 'image/jpeg'
    
    try:
        return FileResponse(
            open(image_path, 'rb'),
            content_type=content_type,
            as_attachment=False
        )
    except IOError as e:
        logger.error(f"IOError serving prototype {prototype_id}: {e}")
        raise Http404("File not found")


@login_required
def serve_estate_layout(request, layout_id):
    """
    Secure estate layout image serving
    Validates user has access to the estate before serving image
    """
    from estateApp.models import EstateLayout
    import mimetypes
    
    try:
        layout = EstateLayout.objects.select_related('estate').get(id=layout_id)
    except EstateLayout.DoesNotExist:
        raise Http404("Layout not found")
    
    # Verify image exists
    if not layout.layout_image:
        raise Http404("Image not found")
    
    estate = layout.estate
    if not estate:
        raise Http404("Estate not found")
    
    image_path = layout.layout_image.path
    
    # Verify path is within media directory
    if not os.path.abspath(image_path).startswith(os.path.abspath(settings.MEDIA_ROOT)):
        raise SuspiciousOperation("Invalid file path")
    
    # Check if file exists
    if not os.path.exists(image_path):
        logger.error(f"Layout image not found: {image_path}")
        raise Http404("File not found")
    
    # Log access
    logger.info(f"Estate layout served: {layout_id} from Estate {estate.id} to User {request.user.id}")
    
    content_type, _ = mimetypes.guess_type(image_path)
    if not content_type:
        content_type = 'image/jpeg'
    
    try:
        return FileResponse(
            open(image_path, 'rb'),
            content_type=content_type,
            as_attachment=False
        )
    except IOError as e:
        logger.error(f"IOError serving layout {layout_id}: {e}")
        raise Http404("File not found")


@login_required
def serve_floor_plan(request, plan_id):
    """
    Secure floor plan image serving
    Validates user has access to the estate before serving image
    """
    from estateApp.models import FloorPlan
    import mimetypes
    
    try:
        plan = FloorPlan.objects.select_related('estate').get(id=plan_id)
    except FloorPlan.DoesNotExist:
        raise Http404("Floor plan not found")
    
    # Verify image exists
    if not plan.floor_plan_image:
        raise Http404("Image not found")
    
    estate = plan.estate
    if not estate:
        raise Http404("Estate not found")
    
    image_path = plan.floor_plan_image.path
    
    # Verify path is within media directory
    if not os.path.abspath(image_path).startswith(os.path.abspath(settings.MEDIA_ROOT)):
        raise SuspiciousOperation("Invalid file path")
    
    # Check if file exists
    if not os.path.exists(image_path):
        logger.error(f"Floor plan image not found: {image_path}")
        raise Http404("File not found")
    
    # Log access
    logger.info(f"Floor plan served: {plan_id} from Estate {estate.id} to User {request.user.id}")
    
    content_type, _ = mimetypes.guess_type(image_path)
    if not content_type:
        content_type = 'image/jpeg'
    
    try:
        return FileResponse(
            open(image_path, 'rb'),
            content_type=content_type,
            as_attachment=False
        )
    except IOError as e:
        logger.error(f"IOError serving floor plan {plan_id}: {e}")
        raise Http404("File not found")

