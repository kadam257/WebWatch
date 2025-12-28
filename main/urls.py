from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('create/', views.create_party, name='create_party'),
    path('party/<int:party_id>/', views.watch_party, name='watch_party'),
]
