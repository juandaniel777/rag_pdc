from django.urls import path
from . import views

urlpatterns = [
    path('sugerir-rae', views.sugerir_rae, name='sugerir-rae'),
]
