import json
import hashlib
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.urls import reverse
from django.conf import settings
from rest_framework.test import APITestCase
from rest_framework import status

from .models import Product, Order, OrderItem

# ==================== MODEL TESTS ====================

class ProductModelTests(APITestCase):
    """Test Product model methods"""
    
    def setUp(self):
        self.product = Product.objects.create(
            name="Test Laptop", 
            price=Decimal('1000.00'), 
            stock=5
        )

    def test_product_str_method(self):
        """Test Product __str__ method"""
        expected = f"{self.product.name} - Stock: {self.product.stock}"
        self.assertEqual(str(self.product), expected)

class OrderModelTests(APITestCase):
    """Test Order model methods"""
    
    def setUp(self):
        self.order = Order.objects.create(
            customer_name="Test User",
            customer_email="test@example.com",
            total_price=Decimal('1000.00')
        )

    def test_order_str_method(self):
        """Test Order __str__ method"""
        self.assertIn("Order", str(self.order))
        self.assertIn(self.order.status, str(self.order))

    def test_order_uuid_generation(self):
        """Test order_id is automatically generated"""
        self.assertIsNotNone(self.order.order_id)
        self.assertEqual(len(str(self.order.order_id)), 36)  # UUID length

class OrderItemModelTests(APITestCase):
    """Test OrderItem model methods"""
    
    def setUp(self):
        self.product = Product.objects.create(
            name="Test Laptop", 
            price=Decimal('1000.00'), 
            stock=5
        )
        self.order = Order.objects.create(
            customer_name="Test User",
            customer_email="test@example.com"
        )
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=2,
            price=self.product.price
        )

    def test_order_item_str_method(self):
        """Test OrderItem __str__ method"""
        expected = f"{self.order_item.quantity} x {self.product.name}"
        self.assertEqual(str(self.order_item), expected)

# ==================== SERIALIZER TESTS ====================

class SerializerTests(APITestCase):
    """Test serializer validation logic"""
    
    def setUp(self):
        self.product1 = Product.objects.create(
            name="Laptop", 
            price=Decimal('1000.00'), 
            stock=5
        )
        self.product2 = Product.objects.create(
            name="Mouse", 
            price=Decimal('50.00'), 
            stock=10
        )
        self.valid_payload = {
            "customer_name": "John Doe",
            "customer_email": "john@example.com",
            "items": [
                {"product": self.product1.id, "quantity": 2},
                {"product": self.product2.id, "quantity": 1}
            ]
        }

    def test_valid_payload_passes(self):
        """Test that valid payload passes validation"""
        from .serializers import OrderSerializer
        serializer = OrderSerializer(data=self.valid_payload)
        self.assertTrue(serializer.is_valid())

    def test_empty_customer_name_fails(self):
        """Test empty customer name fails validation"""
        from .serializers import OrderSerializer
        payload = self.valid_payload.copy()
        payload["customer_name"] = ""
        serializer = OrderSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn("customer_name", serializer.errors)

    def test_invalid_email_fails(self):
        """Test invalid email format fails validation"""
        from .serializers import OrderSerializer
        payload = self.valid_payload.copy()
        payload["customer_email"] = "invalid-email"
        serializer = OrderSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn("customer_email", serializer.errors)

    def test_empty_items_fails(self):
        """Test empty items list fails validation"""
        from .serializers import OrderSerializer
        payload = self.valid_payload.copy()
        payload["items"] = []
        serializer = OrderSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn("items", serializer.errors)

    def test_negative_quantity_fails(self):
        """Test negative quantity fails validation"""
        from .serializers import OrderItemSerializer
        serializer = OrderItemSerializer(data={
            "product": self.product1.id, 
            "quantity": -1
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn("quantity", serializer.errors)

    def test_product_not_found_fails(self):
        """Test non-existent product fails validation"""
        from .serializers import OrderSerializer
        payload = self.valid_payload.copy()
        payload["items"] = [{"product": 999, "quantity": 1}]
        serializer = OrderSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn("items", serializer.errors)

    def test_duplicate_products_merged_for_stock_check(self):
        """Test duplicate products are merged correctly for stock validation"""
        from .serializers import OrderSerializer
        payload = {
            "customer_name": "John Doe",
            "customer_email": "john@example.com",
            "items": [
                {"product": self.product1.id, "quantity": 3},
                {"product": self.product1.id, "quantity": 2}  # Total 5, stock is 5
            ]
        }
        serializer = OrderSerializer(data=payload)
        self.assertTrue(serializer.is_valid())

    def test_insufficient_stock_fails(self):
        """Test insufficient stock fails validation"""
        from .serializers import OrderSerializer
        payload = {
            "customer_name": "John Doe",
            "customer_email": "john@example.com",
            "items": [{"product": self.product1.id, "quantity": 6}]  # Stock is 5
        }
        serializer = OrderSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn("items", serializer.errors)

# ==================== PRODUCT API TESTS ====================

class ProductAPITests(APITestCase):
    """Test Product API endpoints"""
    
    def setUp(self):
        self.product1 = Product.objects.create(
            name="Laptop", 
            price=Decimal('1000.00'), 
            stock=5
        )
        self.product2 = Product.objects.create(
            name="Mouse", 
            price=Decimal('50.00'), 
            stock=10
        )
        self.product_list_url = reverse('product-list')

    def test_get_product_list(self):
        """Test GET /api/products/ returns all products"""
        response = self.client.get(self.product_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

# ==================== CHECKOUT TESTS ====================

class CheckoutTests(APITestCase):
    """Test checkout API endpoints"""
    
    def setUp(self):
        self.product1 = Product.objects.create(
            name="Laptop", 
            price=Decimal('1000.00'), 
            stock=5
        )
        self.product2 = Product.objects.create(
            name="Mouse", 
            price=Decimal('50.00'), 
            stock=10
        )
        self.checkout_url = reverse('checkout')
        self.valid_payload = {
            "customer_name": "John Doe",
            "customer_email": "john@example.com",
            "items": [
                {"product": self.product1.id, "quantity": 2},
                {"product": self.product2.id, "quantity": 1}
            ]
        }
        
    @patch('api.views.snap.create_transaction')
    def test_checkout_success(self, mock_create_transaction):
        """Test successful checkout with valid data"""
        mock_create_transaction.return_value = {
            'redirect_url': 'https://app.sandbox.midtrans.com/pay',
            'token': 'mock-token-123'
        }

        response = self.client.post(
            self.checkout_url, 
            data=self.valid_payload, 
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('order_id', response.data)
        self.assertIn('payment_url', response.data)
        self.assertIn('token', response.data)
        self.assertEqual(response.data['total_price'], '2050.00')

        # Verify stock is reduced
        self.product1.refresh_from_db()
        self.product2.refresh_from_db()
        self.assertEqual(self.product1.stock, 3)
        self.assertEqual(self.product2.stock, 9)

        # Verify order created
        order = Order.objects.get(order_id=response.data['order_id'])
        self.assertEqual(order.total_price, Decimal('2050.00'))
        self.assertEqual(order.status, 'PENDING')
        self.assertEqual(order.items.count(), 2)
        self.assertEqual(order.customer_name, "John Doe")
        self.assertEqual(order.customer_email, "john@example.com")

    def test_checkout_insufficient_stock(self):
        """Test checkout with insufficient stock"""
        payload = {
            "customer_name": "John Doe",
            "customer_email": "john@example.com",
            "items": [{"product": self.product1.id, "quantity": 6}]
        }
        
        response = self.client.post(
            self.checkout_url, 
            data=payload, 
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Verify stock is NOT reduced
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.stock, 5)

    def test_checkout_missing_required_fields(self):
        """Test checkout with missing required fields"""
        # Missing customer_name
        payload = {
            "customer_email": "john@example.com",
            "items": [{"product": self.product1.id, "quantity": 1}]
        }
        
        response = self.client.post(
            self.checkout_url, 
            data=payload, 
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('customer_name', response.data)

    @patch('api.views.snap.create_transaction')
    def test_checkout_midtrans_api_error(self, mock_create_transaction):
        """Test checkout when Midtrans API fails"""
        mock_create_transaction.side_effect = Exception("Midtrans API Error")
        
        response = self.client.post(
            self.checkout_url, 
            data=self.valid_payload, 
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn('error', response.data)

# ==================== WEBHOOK TESTS ====================

class WebhookTests(APITestCase):
    """Test Midtrans webhook handling"""
    
    def setUp(self):
        self.product = Product.objects.create(
            name="Laptop", 
            price=Decimal('1000.00'), 
            stock=5
        )
        self.order = Order.objects.create(
            customer_name="John Doe",
            customer_email="john@example.com",
            total_price=Decimal('1000.00'),
            status='PENDING'
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=1,
            price=self.product.price
        )
        self.webhook_url = reverse('midtrans-webhook')
        self.server_key = settings.MIDTRANS_SERVER_KEY

    def generate_signature(self, order_id, status_code, gross_amount):
        """Helper to generate valid signature"""
        payload = f"{order_id}{status_code}{gross_amount}{self.server_key}"
        return hashlib.sha512(payload.encode('utf-8')).hexdigest()

    def test_webhook_valid_signature_settlement(self):
        """Test valid webhook with settlement status"""
        order_id = str(self.order.order_id)
        status_code = "200"
        gross_amount = str(int(self.order.total_price))
        
        signature = self.generate_signature(order_id, status_code, gross_amount)

        payload = {
            "order_id": order_id,
            "status_code": status_code,
            "gross_amount": gross_amount,
            "signature_key": signature,
            "transaction_status": "settlement"
        }

        response = self.client.post(
            self.webhook_url, 
            data=payload, 
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'PAID')

    def test_webhook_valid_signature_capture(self):
        """Test valid webhook with capture status"""
        order_id = str(self.order.order_id)
        status_code = "200"
        gross_amount = str(int(self.order.total_price))
        
        signature = self.generate_signature(order_id, status_code, gross_amount)

        payload = {
            "order_id": order_id,
            "status_code": status_code,
            "gross_amount": gross_amount,
            "signature_key": signature,
            "transaction_status": "capture"
        }

        response = self.client.post(
            self.webhook_url, 
            data=payload, 
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'PAID')

    def test_webhook_cancel_status(self):
        """Test webhook with cancel status"""
        order_id = str(self.order.order_id)
        status_code = "200"
        gross_amount = str(int(self.order.total_price))
        
        signature = self.generate_signature(order_id, status_code, gross_amount)

        payload = {
            "order_id": order_id,
            "status_code": status_code,
            "gross_amount": gross_amount,
            "signature_key": signature,
            "transaction_status": "cancel"
        }

        response = self.client.post(
            self.webhook_url, 
            data=payload, 
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'FAILED')

    def test_webhook_deny_status(self):
        """Test webhook with deny status"""
        order_id = str(self.order.order_id)
        status_code = "200"
        gross_amount = str(int(self.order.total_price))
        
        signature = self.generate_signature(order_id, status_code, gross_amount)

        payload = {
            "order_id": order_id,
            "status_code": status_code,
            "gross_amount": gross_amount,
            "signature_key": signature,
            "transaction_status": "deny"
        }

        response = self.client.post(
            self.webhook_url, 
            data=payload, 
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'FAILED')

    def test_webhook_expire_status(self):
        """Test webhook with expire status"""
        order_id = str(self.order.order_id)
        status_code = "200"
        gross_amount = str(int(self.order.total_price))
        
        signature = self.generate_signature(order_id, status_code, gross_amount)

        payload = {
            "order_id": order_id,
            "status_code": status_code,
            "gross_amount": gross_amount,
            "signature_key": signature,
            "transaction_status": "expire"
        }

        response = self.client.post(
            self.webhook_url, 
            data=payload, 
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'EXPIRED')

    def test_webhook_invalid_signature(self):
        """Test webhook with invalid signature"""
        payload = {
            "order_id": str(self.order.order_id),
            "status_code": "200",
            "gross_amount": "1000",
            "signature_key": "invalid-signature",
            "transaction_status": "settlement"
        }

        response = self.client.post(
            self.webhook_url, 
            data=payload, 
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'PENDING')

    def test_webhook_missing_fields(self):
        """Test webhook with missing required fields"""
        payload = {
            "order_id": str(self.order.order_id),
            "status_code": "200",
        }

        response = self.client.post(
            self.webhook_url, 
            data=payload, 
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_webhook_order_not_found(self):
        """Test webhook with non-existent order"""
        signature = self.generate_signature("invalid-order", "200", "1000")
        
        payload = {
            "order_id": "invalid-order",
            "status_code": "200",
            "gross_amount": "1000",
            "signature_key": signature,
            "transaction_status": "settlement"
        }

        response = self.client.post(
            self.webhook_url, 
            data=payload, 
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_webhook_idempotent_duplicate(self):
        """Test webhook doesn't process duplicate notifications"""
        # First, set order to PAID
        self.order.status = 'PAID'
        self.order.save()

        order_id = str(self.order.order_id)
        status_code = "200"
        gross_amount = str(int(self.order.total_price))
        
        signature = self.generate_signature(order_id, status_code, gross_amount)

        payload = {
            "order_id": order_id,
            "status_code": status_code,
            "gross_amount": gross_amount,
            "signature_key": signature,
            "transaction_status": "settlement"
        }

        response = self.client.post(
            self.webhook_url, 
            data=payload, 
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], "Order already processed before")
        
        # Status should still be PAID
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'PAID')