# Sistem Checkout API (Assmblr Tech Test)

Sebuah sistem *checkout* sederhana yang dibangun menggunakan Django dan Django REST Framework, terintegrasi penuh dengan Midtrans Sandbox.

## Persyaratan Sistem (Prerequisites)
- Python 3.10 atau versi lebih baru
- `pip` (Rekomendasi menggunakan `virtualenv`)
- PostgreSQL (Menggunakan database Supabase seperti yang telah dikonfigurasi di `.env.example`)

---

## Petunjuk Instalasi & Menjalankan Aplikasi

1. **Clone repository ini** 
2. **Masuk ke dalam direktori proyek**:
   ```bash
   cd "assmblr tech test"
   ```
3. **Buat virtual environment**:
   ```bash
   python -m venv venv
   ```
4. **Aktifkan virtual environment**:
   - Untuk **Windows**: 
     ```bash
     .\venv\Scripts\activate
     ```
   - Untuk **Mac/Linux**: 
     ```bash
     source venv/bin/activate
     ```
5. **Konfigurasi Environment Variables (`.env`)**:
   Salin file `.env.example` menjadi `.env`:
   ```bash
   cp .env.example .env
   ```
   *Buka file `.env` dan masukkan Server Key serta Client Key dari Midtrans Sandbox Anda. Jika Anda ingin mengetes koneksi Supabase asli proyek ini, biarkan `DATABASE_URL` sesuai pada file `.env.example`.*

7. **Jalankan Migrasi Database**:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```
8. **(Opsional) Buat Akun Superuser & Data Dummy**:
   Anda dapat membuat akun admin untuk memasukkan data produk tiruan (dummy) via Django Admin Panel (`http://127.0.0.1:8000/admin`).
   ```bash
   python manage.py createsuperuser
   ```
   *(Atau Anda bisa menggunakan `python manage.py shell` untuk membuat produk).*

9. **Jalankan Server Lokal**:
   ```bash
   python manage.py runserver
   ```

---

## Panduan Pengujian (Testing)

### 1. Pengujian Otomatis (Automated Unit Tests)
Proyek ini sudah dilengkapi dengan \`26 skenario pengujian unit\` komprehensif (meliputi *race condition*, *stock check*, kalkulasi total, validasi webhook, dll). 
Jalankan tes menggunakan perintah berikut (pastikan virtual environment aktif):
```bash
python manage.py test api -v 2
```

### 2. Pengujian API Manual (Via Postman/Insomnia)

*Pastikan server django (`python manage.py runserver`) sedang menyala.*

#### A. Cek Daftar Produk
- **Metode**: `GET`
- **URL**: `http://127.0.0.1:8000/api/products/`
- **Fungsi**: Melihat ID produk, nama, harga, dan ketersediaan stok.

#### B. Membuat Order (Checkout)
- **Metode**: `POST`
- **URL**: `http://127.0.0.1:8000/api/checkout/`
- **Headers**: `Content-Type: application/json`
- **Payload Contoh**:
  ```json
  {
      "customer_name": "Zikra Fadly",
      "customer_email": "zikra@example.com",
      "items": [
          {"product": 1, "quantity": 2}
      ]
  }
  ```
- **Fungsi**: Memeriksa stok produk (menolaknya jika kurang), mengunci baris DB (*Row Locking*), mengurangi stok, menghitung harga total (*backend server-side*), dan me-return `payment_url` (halaman pembayaran Midtrans Sandbox).

#### C. Simulasi Notifikasi Webhook Midtrans
- **Metode**: `POST`
- **URL**: `http://127.0.0.1:8000/api/webhook/`
- **Headers**: `Content-Type: application/json`
- **Fungsi**: Menyimulasikan _update_ riil dari server Midtrans. Memvalidasi algoritma `signature_key` (SHA512) demi keamanan, lalu melakukan *idempotency check* untuk menghindari pemrosesan data ganda untuk Order yang sama.

---

## Fitur Unggulan (Pemenuhan Requirement Tech Test)
1. **Keamanan Transaksi Database**: Menggunakan blok `with transaction.atomic()` dan `select_for_update()` pada Checkout dan Webhook guna mencegah *Race Condition* saat banyak pengguna bertransaksi di waktu bersamaan.
2. **Kalkulasi Aman di Backend**: Perhitungan `total_price` diotomatisasi sepelanuhya oleh server demi menghindari manipulasi harga oleh _client_.
3. **Idempotent Webhook**: Antisipasi penanganan notifikasi *duplicate* dari Midtrans; sistem tidak akan merusak status Order yang sudah berstatus Final.
4. **Validasi Signature Midtrans**: Endpoint Webhook tidak bergantung pada login *user*, namun diamankan dengan metode keamanan kalkulasi Hash SHA512 rahasia antara server lokal dan Midtrans.
5. **Konfigurasi Berbasis Lingkungan**: Menghindari aksi "*Hardcode Credential*" dengan meletakkan konfigurasi krusial pada _environment variables_ menggunakan package `python-dotenv`.
