from estateApp.models import CustomUser, Company
from estateApp.backends import EmailBackend
from django.contrib.auth import authenticate
from django.test import RequestFactory
from estateApp.views import CustomLoginView
from estateApp.forms import CustomAuthenticationForm
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.middleware import AuthenticationMiddleware
from datetime import date

# Create a test company first
company, created = Company.objects.get_or_create(
    company_name='Test Company',
    defaults={
        'registration_number': 'TEST123',
        'registration_date': date.today(),
        'location': 'Test Location',
        'ceo_name': 'Test CEO',
        'ceo_dob': date.today(),
        'email': 'company@test.com',
        'phone': '1234567890'
    }
)

# Create test users
try:
    user1 = CustomUser.objects.get(email='test@example.com', role='admin')
except:
    user1 = CustomUser.objects.create_user(
        email='test@example.com',
        full_name='Test Admin',
        phone='1234567890',
        password='password123',
        role='admin',
        company_profile=company
    )

try:
    user2 = CustomUser.objects.get(email='test@example.com', role='client')
except:
    user2 = CustomUser.objects.create_user(
        email='test@example.com',
        full_name='Test Client',
        phone='1234567891',
        password='password123',
        role='client',
        company_profile=None
    )

try:
    user3 = CustomUser.objects.get(email='test@example.com', role='marketer')
except:
    user3 = CustomUser.objects.create_user(
        email='test@example.com',
        full_name='Test Marketer',
        phone='1234567892',
        password='password123',
        role='marketer',
        company_profile=None
    )

print('Created test users')

# Test authentication backend
backend = EmailBackend()
result = backend.authenticate(None, username='test@example.com', password='password123')
print(f'Backend result: {result}')
print(f'Backend result type: {type(result)}')
if hasattr(result, 'users'):
    print(f'Number of users: {len(result.users)}')
    for user in result.users:
        print(f'User: {user.full_name} ({user.role})')

# Test form
factory = RequestFactory()
request = factory.post('/login/', {'username': 'test@example.com', 'password': 'password123'})

# Add session middleware properly
middleware = SessionMiddleware(lambda r: None)
middleware.process_request(request)
request.session.save()

# Add auth middleware
auth_middleware = AuthenticationMiddleware(lambda r: None)
auth_middleware.process_request(request)

form = CustomAuthenticationForm(data={'username': 'test@example.com', 'password': 'password123'})
is_valid = form.is_valid()
print(f'Form is_valid: {is_valid}')
print(f'Form errors: {form.errors}')
print(f'Form user: {form.get_user()}')
print(f'Form user type: {type(form.get_user())}')

# Test view form_valid method
view = CustomLoginView()
view.request = request
view.kwargs = {}  # Set kwargs to avoid AttributeError

# Call form_valid directly to simulate POST submission
response = view.form_valid(form)
print(f'Form valid response status: {response.status_code}')
print(f'Form valid response has modal: {"roleSelectionModal" in response.content.decode("utf-8")}')
print(f'Form valid response content length: {len(response.content)}')

# Check if the response contains the multiple_users context
content = response.content.decode('utf-8')
if 'multiple_users' in content:
    print('SUCCESS: Response contains multiple_users')
else:
    print('ISSUE: Response does not contain multiple_users')

# Test template rendering directly
from django.template.loader import get_template

template = get_template('auth/unified_login.html')
context = {
    'multiple_users': [user1, user2, user3],
    'user_email': 'test@example.com',
    'form': form,
    'honeypot_field': 'honeypot',
    'login_slug': None
}

rendered_html = template.render(context)
print(f'Template rendered successfully: {len(rendered_html)} characters')
print(f'Template contains modal: {"roleSelectionModal" in rendered_html}')
print(f'Template contains user options: {rendered_html.count("role-option")} user options found')