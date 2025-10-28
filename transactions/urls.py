from django.urls import path
from . import views

app_name = 'transactions'

urlpatterns = [
    path('purchase-request/<int:listing_pk>/create/', views.purchase_request_create, name='purchase_request_create'),
    path('purchase-request/<int:pk>/', views.purchase_request_detail, name='purchase_request_detail'),
    path('purchase-request/<int:pk>/accept/', views.purchase_request_accept, name='purchase_request_accept'),
    path('purchase-request/<int:pk>/reject/', views.purchase_request_reject, name='purchase_request_reject'),
    path('purchase-request/<int:pk>/complete/', views.purchase_request_complete, name='purchase_request_complete'),
    path('purchase-request/<int:pk>/cancel/', views.purchase_request_cancel, name='purchase_request_cancel'),
    path('review/<int:purchase_request_pk>/create/', views.review_create, name='review_create'),
]

