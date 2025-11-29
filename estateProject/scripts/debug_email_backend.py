import os, sys
# Ensure project root is on sys.path so Django settings module can be imported
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
os.environ['DJANGO_SETTINGS_MODULE'] = 'estateProject.settings'
import django
django.setup()
from estateApp.backends import EmailBackend
from unittest.mock import patch

class FakeUser:
    def __init__(self, email, pw_ok, role='client'):
        self.email = email
        self._pw_ok = pw_ok
        self.role = role
    def check_password(self, pw):
        return self._pw_ok

users = [FakeUser('a@example.com', True, 'client'), FakeUser('a@example.com', True, 'marketer')]

with patch('estateApp.backends.CustomUser.objects.filter', return_value=users):
    res = EmailBackend().authenticate(request=None, username='a@example.com', password='pw')
    print('RES:', type(res), res)
