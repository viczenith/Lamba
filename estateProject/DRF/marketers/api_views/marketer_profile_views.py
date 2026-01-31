from rest_framework.views import APIView
from rest_framework import permissions
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import serializers as drf_serializers

from DRF.marketers.serializers.marketer_profile_serializers import MarketerProfileSerializer
from DRF.shared_drf import APIResponse
from estateApp.models import MarketerUser, MarketerAffiliation, Transaction, ClientUser


class IsMarketer(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        # allow staff/admins too so admin pages can view
        if getattr(request.user, 'is_staff', False) or getattr(request.user, 'is_superuser', False):
            return True
        return getattr(request.user, 'role', '') == 'marketer'


class MarketerProfileView(APIView):
    """
    GET: returns the marketer's profile + performance + leaderboard data.
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (permissions.IsAuthenticated, IsMarketer)

    def get(self, request, *args, **kwargs):
        user = request.user
        # Allow staff/admin to view other marketer profiles via ?marketer_id for admin pages / support
        marketer_id = request.query_params.get('marketer_id')
        try:
            if marketer_id and (getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False)):
                marketer = MarketerUser.objects.filter(pk=marketer_id).first()
            else:
                marketer = MarketerUser.objects.filter(pk=user.id).first()

            if not marketer:
                return APIResponse.not_found(
                    message='Marketer profile not found',
                    error_code='MARKETER_NOT_FOUND'
                )
        except Exception:
            return APIResponse.server_error(
                message='Could not locate marketer.',
                error_code='MARKETER_LOOKUP_ERROR'
            )

        serializer = MarketerProfileSerializer(marketer, context={'request': request})
        return APIResponse.success(
            data=serializer.data,
            message='Marketer profile retrieved'
        )


class MarketerProfileUpdateView(APIView):
    """
    POST multipart/form-data to update marketer fields (about, company, job, country, profile_image).
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated, IsMarketer)
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        user = request.user
        marketer_id = request.data.get('marketer_id') or request.query_params.get('marketer_id')
        try:
            # staff may update other marketers when marketer_id is provided
            if marketer_id and (getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False)):
                marketer = MarketerUser.objects.filter(pk=marketer_id).first()
            else:
                marketer = MarketerUser.objects.filter(pk=user.id).first()

            if not marketer:
                return APIResponse.not_found(
                    message='Marketer not found',
                    error_code='MARKETER_NOT_FOUND'
                )
        except Exception:
            return APIResponse.server_error(
                message='Could not locate marketer.',
                error_code='MARKETER_LOOKUP_ERROR'
            )

        updatable = ['about', 'company', 'job', 'country']
        for f in updatable:
            if f in request.data:
                setattr(marketer, f, request.data.get(f) or None)

        # Validate profile image uploads (basic checks)
        if 'profile_image' in request.FILES:
            img = request.FILES['profile_image']
            content_type = getattr(img, 'content_type', '')
            max_size = 2 * 1024 * 1024  # 2MB
            if not content_type.startswith('image/'):
                return APIResponse.validation_error(
                    errors={'profile_image': ['Uploaded file must be an image.']},
                    error_code='INVALID_FILE_TYPE'
                )
            if getattr(img, 'size', 0) > max_size:
                return APIResponse.validation_error(
                    errors={'profile_image': ['Image exceeds maximum size of 2MB.']},
                    error_code='FILE_TOO_LARGE'
                )
            marketer.profile_image = img

        marketer.save()
        serializer = MarketerProfileSerializer(marketer, context={'request': request})
        return APIResponse.success(
            data=serializer.data,
            message='Marketer profile updated'
        )


class ChangePasswordSerializer(drf_serializers.Serializer):
    current_password = drf_serializers.CharField(required=True)
    new_password = drf_serializers.CharField(required=True, min_length=6)

class MarketerChangePasswordView(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated, IsMarketer)

    def post(self, request, *args, **kwargs):
        serializer = ChangePasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.validation_error(
                errors=serializer.errors,
                error_code='VALIDATION_FAILED'
            )

        user = request.user
        current = serializer.validated_data['current_password']
        new = serializer.validated_data['new_password']

        if not user.check_password(current):
            return APIResponse.validation_error(
                errors={'current_password': ['Current password is incorrect.']},
                error_code='INVALID_CREDENTIALS'
            )

        user.set_password(new)
        user.save()
        return APIResponse.success(
            data=None,
            message='Password updated successfully'
        )


class MarketerTransactionsView(APIView):
    """
    GET: list transactions where the marketer is the assigned marketer.
    This supports the "Deals" listing for a marketer dashboard.
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (permissions.IsAuthenticated, IsMarketer)

    def get(self, request, *args, **kwargs):
        user = request.user
        marketer_id = request.query_params.get('marketer_id')
        company_id = request.query_params.get('company_id')

        # resolve marketer (allow staff to query others)
        if marketer_id and (getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False)):
            marketer = MarketerUser.objects.filter(pk=marketer_id).first()
        else:
            marketer = getattr(user, 'id', None) and MarketerUser.objects.filter(pk=user.id).first()

        if not marketer:
            return APIResponse.not_found(message='Marketer not found', error_code='MARKETER_NOT_FOUND')

        # Determine affiliated companies to enforce scoping
        affiliated_company_ids = list(
            MarketerAffiliation.objects.filter(marketer=marketer).values_list('company_id', flat=True)
        )
        own_company_id = getattr(marketer, 'company_profile_id', None)
        if own_company_id and own_company_id not in affiliated_company_ids:
            affiliated_company_ids.append(own_company_id)

        # include companies where the marketer has transactions
        txn_company_ids = list(
            Transaction.objects.filter(marketer=marketer).values_list('company_id', flat=True).distinct()
        )
        for cid in txn_company_ids:
            if cid and cid not in affiliated_company_ids:
                affiliated_company_ids.append(cid)

        qs = (
            Transaction.objects
            .filter(marketer=marketer, company_id__in=affiliated_company_ids)
            .select_related('client', 'allocation__estate', 'allocation__plot_size_unit')
            .prefetch_related('payment_records')
        )

        # optional narrower company filter (must be within affiliated companies unless staff explicitly bypasses)
        if company_id:
            try:
                cid = int(company_id)
                if cid in affiliated_company_ids or getattr(user, 'is_staff', False):
                    qs = qs.filter(company_id=cid)
                else:
                    return APIResponse.forbidden(message='Company not within marketer affiliation')
            except Exception:
                pass

        # import here to avoid circular imports
        from DRF.clients.serializers.client_profile_serializer import TransactionSerializer
        serializer = TransactionSerializer(qs, many=True, context={'request': request})
        return APIResponse.success(
            data=serializer.data,
            message='Transactions retrieved'
        )

