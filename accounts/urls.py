from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = 'accounts'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('base/', views.base_view, name='base'),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(next_page='accounts:login'), name='logout'),
    path('profile/', views.profile_view, name='profile'),
]
