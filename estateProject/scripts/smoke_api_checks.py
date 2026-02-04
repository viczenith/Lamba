#!/usr/bin/env python3
import os
import sys
import pathlib
# ensure project root on path
BASE_DIR = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))
import django
import json
import pprint

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

urls = [
    '/api/client/dashboard/',
    '/api/price-update/1/',
    '/api/active-promotions/',
    '/api/promotions/',
    '/api/promotion/1/',
    '/api/estates/',
]

client = Client(HTTP_X_REQUESTED_WITH='XMLHttpRequest', HTTP_USER_AGENT='Mozilla/5.0')
user = get_user_model().objects.filter(is_superuser=True).first()
if not user:
    raise SystemExit('No superuser found to authenticate as. Create one or adjust the script to use another user.')

client.force_login(user)

results = []
for url in urls:
    try:
        r = client.get(url)
        ct = r.get('Content-Type')
        body = r.content.decode('utf-8', 'replace')
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = body[:4000]
        results.append({'url': url, 'status': r.status_code, 'content_type': ct, 'body': parsed})
    except Exception as exc:
        results.append({'url': url, 'error': str(exc)})

pprint.pprint(results)
