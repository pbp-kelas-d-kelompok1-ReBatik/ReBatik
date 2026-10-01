from django.urls import path
from . import views

app_name = 'marketplace'

urlpatterns = [
    path('', views.marketplace_home, name='home'),
    path('drop-off/', views.dropoff_list, name='dropoff'),
]