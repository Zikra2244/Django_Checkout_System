# Checkout System API

A simple checkout system built with Django and Django REST Framework, integrated with Midtrans Sandbox.

## Prerequisites
- Python 3.10+
- `pip` package manager

## Setup Instructions

1. **Clone the repository** (or unzip the folder).
2. **Navigate to the project directory**.
3. **Create a virtual environment**:
   ```bash
   python -m venv venv
   ```
4. **Activate the virtual environment**:
   - On Windows: `.\venv\Scripts\activate`
   - On Mac/Linux: `source venv/bin/activate`
5. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
6. **Set up Environment Variables**:
   Copy `.env.example` to `.env` and fill in your Midtrans Sandbox keys and Supabase connection string:
   ```bash
   cp .env.example .env
   ```
   *Edit `.env` to include your valid `MIDTRANS_SERVER_KEY`, `MIDTRANS_CLIENT_KEY`, and Supabase PostgreSQL `DATABASE_URL`.*
7. **Run Migrations**:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```
8. **(Optional) Create dummy products testing**:
   You can create a superuser and add products via Django Admin (`/admin`), or use `python manage.py shell`.
   ```bash
   python manage.py createsuperuser
   ```
9. **Run the server**:
   ```bash
   python manage.py runserver
   ```

## Running Tests
Run the included unit tests using:
```bash
python manage.py test api
```

## API Endpoints

### 1. List Products
- **Endpoint**: `GET /api/products/`
- **Description**: Returns all available products with stock information.

### 2. Create Order (Checkout)
- **Endpoint**: `POST /api/checkout/`
- **Payload**:
  ```json
  {
      "items": [
          {"product": 1, "quantity": 2},
          {"product": 2, "quantity": 1}
      ]
  }
  ```
- **Description**: Safely reduces stock inside a transaction block, creates an order, calculates total price, and retrieves a Midtrans payment token/URL.

### 3. Midtrans Webhook
- **Endpoint**: `POST /api/webhook/midtrans/`
- **Description**: Webhook listener for Midtrans notifications. Validates signature and updates the order status idempotently.

## Features Met From Requirements
- `transaction.atomic()` used during Checkout and Webhook processing.
- Stock availability checks before reduction (and locks rows to prevent race-conditions using `select_for_update()`).
- Automated total price calculation based on actual product price.
- Duplicate Midtrans webhooks are handled idempotently to only update state logically. 
- Validation of Midtrans signature key via `hashlib.sha512(order_id + status_code + gross_amount + server_key)`.
- Environment variable configuration for secrets and credentials via `python-dotenv`.
