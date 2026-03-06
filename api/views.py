import os
import hashlib
import uuid
from decimal import Decimal
import midtransclient
from django.db import transaction
from django.conf import settings
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .models import Product, Order, OrderItem
from .serializers import ProductSerializer, OrderSerializer

# Ensure midtrans keys are available
assert settings.MIDTRANS_SERVER_KEY, "Missing MIDTRANS_SERVER_KEY"

snap = midtransclient.Snap(
    is_production=False,
    server_key=settings.MIDTRANS_SERVER_KEY,
    client_key=os.environ.get('MIDTRANS_CLIENT_KEY', '')
)

class ProductListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        products = Product.objects.all()
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)


class CheckoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        # Delegate initial validation to the serializer
        serializer = OrderSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        items_data = serializer.validated_data.get('items', [])
        customer_name = serializer.validated_data.get('customer_name')
        customer_email = serializer.validated_data.get('customer_email')
        
        try:
            with transaction.atomic():
                # We want to re-check stock and explicitly lock rows
                total_price = Decimal('0.00')
                order_items_to_create = []

                # Group requests again just to be safe
                product_requests = {}
                for item in items_data:
                    pid = item['product'].id
                    qty = item['quantity']
                    product_requests[pid] = product_requests.get(pid, 0) + qty

                # Lock the products
                locked_products = {
                    p.id: p for p in Product.objects.select_for_update().filter(id__in=product_requests.keys())
                }

                for pid, total_qty in product_requests.items():
                    product = locked_products.get(pid)
                    if product is None:
                        raise ValueError(f"Product not found.")
                    if product.stock < total_qty:
                        raise ValueError(f"Insufficient stock for {product.name}.")
                    
                    product.stock -= total_qty
                    product.save()

                # Create Order dengan customer_name dan customer_email
                order = Order.objects.create(
                    customer_name=customer_name,
                    customer_email=customer_email,
                    total_price=Decimal('0.00')  # Temporary 0, updated below
                )

                for item in items_data:
                    product = locked_products[item['product'].id]
                    qty = int(item['quantity'])
                    price_at_order = Decimal(str(product.price))
                    
                    subtotal = price_at_order * qty
                    total_price += subtotal
                    
                    order_items_to_create.append(
                        OrderItem(
                            order=order, 
                            product=product, 
                            quantity=qty, 
                            price=price_at_order
                        )
                    )

                OrderItem.objects.bulk_create(order_items_to_create)
                order.total_price = total_price
                order.save()

                # Call Midtrans Sandbox
                transaction_details = {
                    "order_id": str(order.order_id),
                    "gross_amount": int(total_price)
                }

                item_details = []
                for item in order_items_to_create:
                    item_details.append({
                        "id": str(item.product.id),
                        "price": int(item.price),
                        "quantity": item.quantity,
                        "name": item.product.name
                    })

                midtrans_payload = {
                    "transaction_details": transaction_details,
                    "item_details": item_details
                }

                midtrans_response = snap.create_transaction(midtrans_payload)

                # Return response dengan total_price sebagai string untuk konsistensi test
                return Response({
                    "order_id": order.order_id,
                    "total_price": str(order.total_price),
                    "payment_url": midtrans_response['redirect_url'],
                    "token": midtrans_response['token']
                }, status=status.HTTP_201_CREATED)

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(f"Error: {e}")  # Untuk debugging
            return Response({"error": "An error occurred during checkout."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MidtransWebhookView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        payload = request.data
        
        order_id = payload.get('order_id')
        status_code = payload.get('status_code')
        gross_amount = payload.get('gross_amount')
        signature_key = payload.get('signature_key')
        transaction_status = payload.get('transaction_status')

        if not all([order_id, status_code, gross_amount, signature_key]):
            return Response({"error": "Missing payload fields"}, status=status.HTTP_400_BAD_REQUEST)

        # Validate signature
        server_key = settings.MIDTRANS_SERVER_KEY
        signature_payload = f"{order_id}{status_code}{gross_amount}{server_key}"
        expected_signature = hashlib.sha512(signature_payload.encode('utf-8')).hexdigest()

        if signature_key != expected_signature:
            return Response({"error": "Invalid signature"}, status=status.HTTP_403_FORBIDDEN)

        # Validasi format UUID - ubah 400 menjadi 404 sesuai test
        try:
            # Coba konversi ke UUID untuk validasi format
            uuid_obj = uuid.UUID(str(order_id))
            order_id = str(uuid_obj)  # Gunakan format string standar
        except (ValueError, AttributeError):
            # Test mengharapkan 404 ketika order tidak ditemukan
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        # Handle valid webhook idempotently inside transaction
        try:
            with transaction.atomic():
                order = Order.objects.select_for_update().get(order_id=order_id)
                
                # Check for duplicate processing
                if order.status in ['PAID', 'FAILED', 'EXPIRED']:
                    # Already processed, return 200 idempotently
                    return Response({"message": "Order already processed before"}, status=status.HTTP_200_OK)
                
                # Update status based on transaction_status
                if transaction_status in ['capture', 'settlement']:
                    order.status = 'PAID'
                elif transaction_status in ['cancel', 'deny']:
                    order.status = 'FAILED'
                elif transaction_status == 'expire':
                    order.status = 'EXPIRED'
                else:
                    # Status lain tidak mengubah status order
                    pass
                
                order.save()
                
            return Response({"message": "Order status updated"}, status=status.HTTP_200_OK)

        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(f"Webhook error: {e}")
            return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)