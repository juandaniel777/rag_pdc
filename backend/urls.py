from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    # Render the existing `templates/index.html` at the site root
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
    # API routes
    path('api/', include('api.urls')),
]
