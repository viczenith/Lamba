from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from estateApp.models import (
    CustomUser, Message, PlotSize, PlotNumber, Estate, PlotSizeUnits, EstatePlot,
    PlotAllocation, Notification, UserNotification, EstateFloorPlan, EstatePrototype,
    EstateAmenitie, EstateLayout, EstateMap, ProgressStatus, PropertyRequest
)

from DRF.company_admin.serializers.user_serializers import CustomUserSerializer
from DRF.company_admin.serializers.message_serializer import MessageSerializer
from DRF.company_admin.serializers.estate_serializers import EstateSerializer
from DRF.company_admin.serializers.plot_and_allocation_serializers import (
    PlotSizeUnitsSerializer, EstatePlotSerializer, PlotAllocationSerializer
)
from DRF.company_admin.serializers.notification_serializers import (
    NotificationSerializer, UserNotificationSerializer
)
from DRF.company_admin.serializers.estate_assets_serializers import (
    EstateFloorPlanSerializer, EstatePrototypeSerializer, EstateAmenitieSerializer,
    EstateLayoutSerializer, EstateMapSerializer, ProgressStatusSerializer
)
from DRF.company_admin.serializers.requests_serializers import (
    PropertyRequestSerializer
)
from DRF.company_admin.serializers.simple_serializers import PlotSizeSerializer, PlotNumberSerializer
from rest_framework.decorators import action
from rest_framework.response import Response




class CustomUserViewSet(viewsets.ModelViewSet):
    serializer_class = CustomUserSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['role']

    def get_queryset(self):
        """Override to ensure company-aware filtering"""
        return CustomUser.objects.all()

    # Add a custom action for the current user
    @action(detail=False, methods=['get'], url_path='me')
    def get_current_user(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Override to ensure company-aware filtering"""
        return Message.objects.all()


class PlotSizeViewSet(viewsets.ModelViewSet):
    serializer_class = PlotSizeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Override to ensure company-aware filtering"""
        return PlotSize.objects.all().order_by('id')


class PlotNumberViewSet(viewsets.ModelViewSet):
    serializer_class = PlotNumberSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Override to ensure company-aware filtering"""
        return PlotNumber.objects.all().order_by('id')


class EstateViewSet(viewsets.ModelViewSet):
    serializer_class = EstateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Override to ensure company-aware filtering"""
        return Estate.objects.all()


class PlotSizeUnitsViewSet(viewsets.ModelViewSet):
    serializer_class = PlotSizeUnitsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Override to ensure company-aware filtering"""
        return PlotSizeUnits.objects.all()


class EstatePlotViewSet(viewsets.ModelViewSet):
    serializer_class = EstatePlotSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Override to ensure company-aware filtering"""
        return EstatePlot.objects.all()


class PlotAllocationViewSet(viewsets.ModelViewSet):
    serializer_class = PlotAllocationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Override to ensure company-aware filtering"""
        return PlotAllocation.objects.all()


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Override to ensure company-aware filtering"""
        return Notification.objects.all()


class UserNotificationViewSet(viewsets.ModelViewSet):
    serializer_class = UserNotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Override to ensure company-aware filtering"""
        return UserNotification.objects.all()


class EstateFloorPlanViewSet(viewsets.ModelViewSet):
    serializer_class = EstateFloorPlanSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Override to ensure company-aware filtering"""
        return EstateFloorPlan.objects.all()


class EstatePrototypeViewSet(viewsets.ModelViewSet):
    serializer_class = EstatePrototypeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Override to ensure company-aware filtering"""
        return EstatePrototype.objects.all()


class EstateAmenitieViewSet(viewsets.ModelViewSet):
    serializer_class = EstateAmenitieSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Override to ensure company-aware filtering"""
        return EstateAmenitie.objects.all()


class EstateLayoutViewSet(viewsets.ModelViewSet):
    serializer_class = EstateLayoutSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Override to ensure company-aware filtering"""
        return EstateLayout.objects.all()


class EstateMapViewSet(viewsets.ModelViewSet):
    serializer_class = EstateMapSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Override to ensure company-aware filtering"""
        return EstateMap.objects.all()


class ProgressStatusViewSet(viewsets.ModelViewSet):
    serializer_class = ProgressStatusSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Override to ensure company-aware filtering"""
        return ProgressStatus.objects.all()


class PropertyRequestViewSet(viewsets.ModelViewSet):
    serializer_class = PropertyRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Override to ensure company-aware filtering"""
        return PropertyRequest.objects.all()




