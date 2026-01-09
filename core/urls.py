from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('search/', views.search_product, name='search_product'),
    path('alert/create/', views.create_alert, name='create_alert'),
]
