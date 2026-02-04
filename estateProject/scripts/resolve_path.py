import os, sys, pathlib
BASE_DIR = pathlib.Path(r"C:\Users\HP\Documents\VictorGodwin\RE\Multi-Tenant Architecture\RealEstateMSApp\estateProject")
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
import django
django.setup()
from django.urls import resolve, Resolver404

paths = ['/api/client/dashboard/', '/client/dashboard/']
for p in paths:
    try:
        match = resolve(p)
        print('PATH:', p)
        print('  func:', match.func)
        print('  view_name:', match.view_name)
        print('  url_name:', match.url_name)
        print('  kwargs:', match.kwargs)
        print('  app_name:', match.app_name)
    except Resolver404 as e:
        print('PATH:', p, '-> Resolver404')
