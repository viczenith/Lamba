from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from .models import *
from .models import Company


class CustomAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        widget=forms.EmailInput(attrs={'autofocus': True, 'placeholder': 'Enter your email'}),
        label="Email",
        required=True
    )
    
    def clean(self):
        """
        Override clean to handle MultipleUserMatch objects.
        When multiple users are found, skip the normal login validation
        and let the view handle the role selection modal.
        """
        from .backends import MultipleUserMatch
        import logging
        logger = logging.getLogger(__name__)
        
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username and password:
            # Attempt to pass tenant/company context when available so the
            # authentication backend can disambiguate users with the same email
            # across companies. The Django AuthenticationForm sets `self.request`
            # when instantiated by the view, so we can try to extract a
            # `login_slug` from the resolver match kwargs.
            company = None
            try:
                if hasattr(self, 'request') and self.request is not None:
                    # Prefer explicit kwargs from URL resolver (e.g., tenant slug)
                    resolver_match = getattr(self.request, 'resolver_match', None)
                    if resolver_match and isinstance(resolver_match.kwargs, dict):
                        login_slug = resolver_match.kwargs.get('login_slug')
                        if login_slug:
                            try:
                                company = Company.objects.get(slug=login_slug)
                            except Company.DoesNotExist:
                                company = None
            except Exception:
                company = None

            # Pass company to authenticate when available
            if company:
                self.user_cache = authenticate(username=username, password=password, company=company)
            else:
                self.user_cache = authenticate(username=username, password=password)
            logger.info(f"Form clean: authenticate returned {self.user_cache}, type: {type(self.user_cache)}")
            
            # If we have multiple users, don't validate as normal user
            if isinstance(self.user_cache, MultipleUserMatch):
                logger.info(f"MultipleUserMatch detected with {len(self.user_cache.users)} users")
                # Skip normal validation - the view will handle this
                return self.cleaned_data
            elif self.user_cache:
                # Normal user validation
                self.confirm_login_allowed(self.user_cache)
            else:
                # No user found
                raise self.get_invalid_login_error()
        
        return self.cleaned_data
    

# ESTATE ADD VIEW FORM

class EstateForm(forms.ModelForm):
    class Meta:
        model = Estate
        fields = ['name', 'location', 'estate_size', 'title_deed']

class EstatePlotForm(forms.ModelForm):
    plot_sizes = forms.ModelMultipleChoiceField(
        queryset=PlotSize.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    plot_numbers = forms.ModelMultipleChoiceField(
        queryset=PlotNumber.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = EstatePlot
        fields = ['estate', 'plot_sizes', 'plot_numbers']



class EstateFloorPlanForm(forms.ModelForm):
    class Meta:
        model = EstateFloorPlan
        fields = ['estate', 'plot_size', 'floor_plan_image', 'plan_title']

# amenities
class AmenitieForm(forms.ModelForm):
    class Meta:
        model = EstateAmenitie
        fields = ['amenities']
        widgets = {
            'amenities': forms.CheckboxSelectMultiple,
        }


# NOTIFICATIONS
class NotificationForm(forms.ModelForm):
    class Meta:
        model = Notification
        fields = ['notification_type', 'title', 'message']
        widgets = {
            'notification_type': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }
        labels = {
            'notification_type': 'Announcement Type',
            'title': 'Title',
            'message': 'Message',
        }

# class EstateValueRegulationForm(forms.ModelForm):
#     class Meta:
#         model = EstateValueRegulation
#         fields = ['estate', 'plot_size', 'current_price', 'effective_date', 'notes']
#         widgets = {
#             'effective_date': forms.DateInput(attrs={'type': 'date'}),
#         }



# COMPANY PROFILE EDIT FORM
class CompanyForm(forms.ModelForm):
    # Make legacy CEO fields optional at the form level so modal can manage CEOs separately
    ceo_name = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    ceo_dob = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    class Meta:
        model = Company
        fields = [
            'company_name', 'registration_number', 'registration_date', 'location',
            'ceo_name', 'ceo_dob', 'email', 'phone', 'logo', 'is_active'
        ]
        widgets = {
            'registration_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'ceo_dob': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

# Optional: inline metrics editor if needed later
class AppMetricsForm(forms.ModelForm):
    class Meta:
        model = AppMetrics
        fields = ['android_downloads', 'ios_downloads']


