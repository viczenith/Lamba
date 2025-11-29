from django.shortcuts import render
from django.http import HttpResponse

def custom_400(request, exception=None):
    return render(request, "errors/400.html", status=400)

def custom_401(request, exception=None):
    return render(request, "errors/401.html", status=401)

def custom_403(request, exception=None):
    return render(request, "errors/403.html", status=403)

def custom_404(request, exception=None):
    return render(request, "errors/404.html", status=404)

def custom_405(request, exception=None):
    return render(request, "errors/405.html", status=405)

def custom_408(request, exception=None):
    return render(request, "errors/408.html", status=408)

def custom_410(request, exception=None):
    return render(request, "errors/410.html", status=410)

def custom_429(request, exception=None):
    return render(request, "errors/429.html", status=429)

def custom_451(request, exception=None):
    return render(request, "errors/451.html", status=451)

def custom_500(request):
    return render(request, "errors/500.html", status=500)

def custom_502(request, exception=None):
    return render(request, "errors/502.html", status=502)

def custom_503(request, exception=None):
    return render(request, "errors/503.html", status=503)

def custom_database_locked(request, exception=None):
    return render(request, "errors/database_locked.html", status=503)
