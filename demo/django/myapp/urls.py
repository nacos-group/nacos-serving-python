from django.urls import path
from . import views

urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('health', views.HealthView.as_view(), name='health'),
    path('info', views.InfoView.as_view(), name='info'),
    path('api/users', views.UsersView.as_view(), name='users'),
    path('api/products', views.ProductsView.as_view(), name='products'),
]
