from rest_framework import serializers
from .models import Product, Order, OrderItem

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'price', 'stock']

class OrderItemSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), write_only=True
    )
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_id = serializers.IntegerField(source='product.id', read_only=True)

    class Meta:
        model = OrderItem
        fields = ['product', 'product_id', 'product_name', 'quantity', 'price']
        read_only_fields = ['price']

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0.")
        return value

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, write_only=True, required=True)
    order_items = OrderItemSerializer(source='items', many=True, read_only=True)
    order_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'order_id', 'customer_name', 'customer_email', 'total_price', 
                  'status', 'created_at', 'items', 'order_items']
        read_only_fields = ['order_id', 'total_price', 'status', 'created_at']
        extra_kwargs = {
            'customer_name': {'required': True, 'allow_blank': False},
            'customer_email': {'required': True, 'allow_blank': False}
        }

    def validate_customer_email(self, value):
        if '@' not in value:
            raise serializers.ValidationError("Enter a valid email address.")
        return value

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Order must have at least one item.")
        product_counts = {}
        product_objects = {}
        
        for item in value:
            product_id = item['product'].id
            quantity = item['quantity']
            try:
                product = Product.objects.get(id=product_id)
                product_objects[product_id] = product
            except Product.DoesNotExist:
                raise serializers.ValidationError(f"Product with ID {product_id} does not exist.")
            if product_id in product_counts:
                product_counts[product_id] += quantity
            else:
                product_counts[product_id] = quantity
        for product_id, total_quantity in product_counts.items():
            product = product_objects[product_id]
            if product.stock < total_quantity:
                raise serializers.ValidationError(
                    f"Insufficient stock for {product.name}. "
                    f"Available: {product.stock}, Requested: {total_quantity}."
                )

        return value

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        order = Order.objects.create(**validated_data)
        
        for item_data in items_data:
            product = item_data['product']
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=item_data['quantity'],
                price=product.price
            )
        
        return order