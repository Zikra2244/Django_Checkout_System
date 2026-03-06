from django.urls import path
from .views import ProductListView, CheckoutView, MidtransWebhookView

urlpatterns = [
    path('products/', ProductListView.as_view(), name='product-list'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('webhook/midtrans/', MidtransWebhookView.as_view(), name='midtrans-webhook'),
]
