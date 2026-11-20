# ReBatik ꕥꕥ

ReBatik adalah platform yang menghadirkan konsep upcycling dengan mengolah pakaian dan kain yang sudah tidak terpakai menjadi karya baru melalui sentuhan seni dan budaya batik Nusantara. Dengan memadukan kreativitas dan warisan budaya Indonesia, ReBatik menghadirkan karya yang tidak hanya ramah lingkungan, tetapi juga memiliki nilai estetika, budaya, dan ekonomis.

## Nama Anggota Kelompok 1 PBP-D

1. Ahyan Timuardi (2506547203)
2. Alisa Selvia Saharani (2506618433)
3. Ausy Dhafa Adhitama (2406417954)
4. M. Rezky Syahputra (2506614006)
5. Rani Faizah A (2506624013)

## Daftar Modul Beserta Deskripsi dan Penanggung Jawabnya

| Modul | Nama Modul | Deskripsi | Penanggung Jawab |
|:---:|---|---|---|
| **Modul&nbsp;1** | Landing Page & Impact Tracker | Menampilkan halaman utama yang memperkenalkan konsep, tujuan, dan manfaat ReBatik dalam mengurangi limbah tekstil. Dilengkapi informasi mengenai permasalahan limbah tekstil, konsep upcycling, serta Impact Tracker yang menyajikan statistik kontribusi pengguna, seperti jumlah kain yang berhasil dialihkan dari limbah. | Ausy Dhafa Adhitama |
| **Modul&nbsp;2** | Batik Custom & Batik Story | Menyediakan fitur Batik Story untuk mempelajari sejarah, asal-usul, filosofi, dan makna budaya berbagai motif batik Indonesia. Batik Custom memungkinkan pengguna membuat desain berdasarkan gender, style, dan color palette. Sistem memberikan rekomendasi desain yang dapat disesuaikan dengan tone warna berdasarkan color palette pilihan pengguna, kemudian diterapkan pada model pakaian yang tersedia di website ReBatik sehingga pengguna dapat melihat hasil desain dan melakukan pemesanan. Inisiatif di Luar Modul: Mengembangkan fitur autentikasi pengguna (Sign In & Sign Up), meningkatkan tampilan dan fungsionalitas navbar, mengembangkan sistem notifikasi untuk memberikan informasi terkait aktivitas pengguna, serta membuat halaman pengaturan (Settings) untuk mendukung pengelolaan akun dan preferensi pengguna. | Alisa Selvia Saharani |
| **Modul&nbsp;3** | Marketplace & Drop-Off Point | Menyediakan Marketplace untuk menjelajahi dan membeli berbagai produk hasil upcycling, lengkap dengan informasi produk, gambar, deskripsi, dan harga. Fitur Drop-Off Point membantu pengguna menemukan lokasi pengumpulan kain atau pakaian bekas agar dapat disalurkan dan dimanfaatkan kembali. | Ahyan Timuardi |
| **Modul&nbsp;4** | Donasi Kain/Pakaian & Profile | Memungkinkan pengguna mengunggah foto dan informasi kain atau pakaian yang ingin didonasikan, termasuk kategori, kondisi, dan deskripsi. Fitur Profile menampilkan informasi akun, riwayat donasi, riwayat pesanan, serta kontribusi pengguna dalam mendukung pengurangan limbah tekstil. | Rani Faizah A |
| **Modul&nbsp;5** | Upcycling Request & Points/Reward | Memungkinkan pengguna mengajukan permintaan pengolahan kain atau pakaian menjadi produk baru dengan memilih jenis produk yang tersedia. Pengguna juga dapat memantau status pengajuan upcycling. Melalui sistem Points/Reward, pengguna memperoleh poin dari aktivitas donasi kain atau pakaian maupun pengajuan upcycling yang berhasil diselesaikan. Poin yang terkumpul dapat ditukarkan dengan voucher diskon untuk berbelanja berbagai produk di Marketplace ReBatik sebagai bentuk apresiasi atas kontribusi pengguna dalam mengurangi limbah tekstil. | M. Rezky Syahputra |

## Sumber/Dokumentasi API

### 1. Public API Eksternal

| Layanan | Endpoint / Metode | Kegunaan | Dokumentasi |
|---|---|---|---|
| API Wilayah Indonesia (emsifa) | `GET https://www.emsifa.com/api-wilayah-indonesia/v2/provinces.json`<br>`GET https://www.emsifa.com/api-wilayah-indonesia/v2/regencies/{province_id}.json`<br>`GET https://www.emsifa.com/api-wilayah-indonesia/v2/districts/{regency_id}.json`<br>`GET https://www.emsifa.com/api-wilayah-indonesia/v2/villages/{district_id}.json` | Dropdown provinsi sampai kelurahan beserta kode pos pada form alamat (Drop-Off Point, Donasi, Upcycling Request). Ganti placeholder ID dengan ID wilayah yang dipilih. | [Dokumentasi emsifa](https://www.emsifa.com/api-wilayah-indonesia/)|

### 2. Mock API ReBatik (Internal Drop-off Point API — 52 Lokasi Spesifik)

Untuk memenuhi kebutuhan data lokasi pengumpulan kain secara spesifik dan terintegrasi lintas platform (Web & Mobile Flutter kelompok), ReBatik menyediakan Mock API titik pengumpulan (*Drop-off Point*) dengan **52 data lokasi riil** di berbagai kota Indonesia. API ini mendukung CORS (`Access-Control-Allow-Origin: *`) dan respons JSON standar.

| Sumber / Lingkungan | Tautan Mock API | Keterangan & Parameter |
|---|---|---|
| **Production (PWS Live)** | `GET https://alisa-selvia-rebatik.pws.cs.ui.ac.id/marketplace/api/dropoff-points/` | Endpoint live seluruh daftar 52 titik drop-off point. |
| **PWS Filter Kota** | `GET https://alisa-selvia-rebatik.pws.cs.ui.ac.id/marketplace/api/dropoff-points/?city=Depok` | Filter titik berdasarkan kota (contoh: `Depok`, `Bandung`, `Solo`, `Jakarta Selatan`, dll). |
| **PWS Filter Pencarian** | `GET https://alisa-selvia-rebatik.pws.cs.ui.ac.id/marketplace/api/dropoff-points/?q=Margonda` | Pencarian teks bebas nama titik / alamat / provinsi. |
| **PWS Detail Titik** | `GET https://alisa-selvia-rebatik.pws.cs.ui.ac.id/marketplace/api/dropoff-points/{code}/` | Detail titik spesifik berdasarkan kode unik (contoh: `rbt-dpk-01`, `rbt-jkt-01`). |
| **Local Development** | `GET http://127.0.0.1:8000/marketplace/api/dropoff-points/` | Digunakan saat pengujian di server lokal Django. |
| **GitHub Raw Mock API** | `https://raw.githubusercontent.com/alisa-selvia/ReBatik/main/marketplace/data/dropoff_points.json` | Mock static JSON direct link tanpa perlu server aktif (cocok untuk integrasi Flutter kelompok). |

<details>
<summary>Contoh Payload JSON Mock API Drop-off Point</summary>

```json
{
  "status": "success",
  "total": 52,
  "filters": { "city": "Depok", "query": "" },
  "data": [
    {
      "code": "rbt-dpk-01",
      "name": "Drop-off ReBatik Margonda Creative Hub",
      "address": "Jl. Margonda No. 240, Kemiri Muka, Kecamatan Beji",
      "city": "Depok",
      "province": "Jawa Barat",
      "operating_hours": "08:30 - 20:00 WIB",
      "latitude": -6.372841,
      "longitude": 106.831518,
      "phone": "+6281299881101",
      "accepted_items": ["Kain Perca Batik", "Baju Batik Bekas", "Sarung & Selendang"],
      "maps_url": "https://www.google.com/maps?q=-6.372841,106.831518",
      "detail_url": "/marketplace/api/dropoff-points/rbt-dpk-01/"
    }
  ]
}
```
</details>

### 3. Data Awal Deployment (Initial Seed Data ≥ 50 Data Utama)

Sesuai ketentuan rubrik PBP (minimal 50 data utama saat dideploy ke PWS), aplikasi ReBatik telah dilengkapi dengan dataset inisial yang otomatis diisi ke database saat `python manage.py migrate` dijalankan:
- **52 Titik Drop-off Point**: Termuat di `marketplace/data/dropoff_points.json`, ter-seed via migrasi `0004_seed_dummy_dropoff_points.py` atau command `python manage.py sync_dropoff_points`.

### 4. API Upcycling dan Rewards

Kedua modul memakai Django REST Framework. Untuk mencoba di Postman atau Flutter, login sekali dan gunakan sesi yang sama untuk panggilan berikutnya.

| Persiapan | Request atau pengaturan | Hasil |
| --- | --- | --- |
| Ambil token awal | `GET /api/v1/auth/csrf/` | Simpan cookie `csrftoken` dan nilai `csrfToken` dari JSON. |
| Login | `POST /api/v1/auth/login/` dengan JSON `{"username":"…","password":"…"}` | Simpan cookie sesi dan CSRF dari respons. Gunakan `csrfToken` terbaru karena login merotasi token. |
| Panggil endpoint | Kirim cookie dan `Accept: application/json`. Pada `POST` dan `PATCH`, sertakan header `X-CSRFToken`. | Gunakan `application/json` untuk data biasa dan `multipart/form-data` untuk unggahan. |

#### Upcycling

Awalan rute adalah `/api/v1/upcycling/`. Ganti `<id>` dengan UUID dari field `id` pengajuan. [Rute](upcycling/api_urls.py) · [Serializer](upcycling/serializers.py)

| Metode dan rute | Akses dan kondisi | Body atau parameter | Respons sukses |
| --- | --- | --- | --- |
| `GET requests/` | Pengguna yang login | — | `200` · Array pengajuan sendiri, terbaru lebih dulu. |
| `POST requests/` | Pengguna dengan kurang dari 10 pengajuan aktif | Multipart seperti contoh di bawah | `201` · Detail pengajuan dengan status `PENDING_ASSIGNMENT`. |
| `GET requests/<id>/` | Pemilik | — | `200` · Detail dengan `whatsapp` dan `custom_product` untuk mengisi form edit, serta `fabric_photos`, `reference_photos`, dan `status_timeline`. |
| `PATCH requests/<id>/` | Pemilik saat `PENDING_ASSIGNMENT` | Field yang berubah, misalnya `{"quantity":2}`. Gunakan multipart untuk menambah foto. | `200` · Detail terbaru. Foto ditambahkan ke koleksi yang sudah ada. |
| `POST requests/<id>/fabric-handoff/` | Pemilik saat `AWAITING_FABRIC`, sebelum tenggat | `fabric_delivery_method` berupa `DROP_OFF` atau `SELF_SHIP`. `fabric_delivery_location` opsional. | `200` · Rencana penyerahan kain tersimpan. |
| `POST requests/<id>/approve-quote/` | Pemilik saat `AWAITING_APPROVAL` dan harga tersedia | Tanpa body | `200` · Status menjadi `AWAITING_DELIVERY_DETAILS`. |
| `POST requests/<id>/product-delivery/` | Pemilik saat `AWAITING_DELIVERY_DETAILS` | `delivery_method` berupa `DROP_OFF` atau `KURIR`, serta `address`. | `200` · Status menjadi `IN_PROGRESS`. |
| `POST requests/<id>/confirm-completion/` | Pemilik saat `READY` | Tanpa body | `200` · Status menjadi `COMPLETED`. Pengguna memperoleh 150 poin sekali untuk pengajuan ini. |
| `POST requests/<id>/cancel/` | Pemilik | `{"action":"cancel"}` saat `PENDING_ASSIGNMENT`, `PENDING_REVIEW`, `AWAITING_FABRIC`, atau `INSPECTION`. Untuk menolak harga saat `AWAITING_APPROVAL`, kirim `{"action":"reject_quote"}`. | `200` · Status menjadi `CANCELLED`. |
| `GET admin/requests/` | Staf | `status` menerima `PENDING_ASSIGNMENT` (default), `PENDING_REVIEW`, atau `IN_PROGRESS`. Gunakan `page` dan `page_size` (default 50, maksimal 100). | `200` · Objek `count`, `next`, `previous`, `results`. Tiap baris memuat `request` dan `artisan_candidates`. |
| `POST admin/requests/<id>/assign-artisan/` | Staf, untuk pengajuan yang menunggu penugasan | Contoh `{"artisan_id":3}`. Ambil ID profil dari `artisan_candidates`. | `200` · Detail pengajuan dengan status `PENDING_REVIEW`. |
| `GET artisan/requests/` | Anggota grup `Artisan` dengan profil upcycling | — | `200` · Array pengajuan yang ditugaskan kepada artisan tersebut. |
| `POST requests/<id>/artisan-action/` | Artisan yang ditugaskan | Objek JSON dengan `action` dan field sesuai tabel aksi di bawah. | `200` · Detail pengajuan setelah transisi. |

**Contoh multipart untuk membuat tote bag dari celana denim.** Di Postman, pilih `POST /api/v1/upcycling/requests/` lalu **Body → form-data**.

| Field | Tipe di Postman | Contoh | Ketentuan |
| --- | --- | --- | --- |
| `fabric` | Text | `DENIM` | Jika `OTHER`, isi juga `fabric_other_description`. |
| `current_item_form` | Text | `PANTS` | Jika `OTHER`, isi juga `current_item_form_other`. |
| `has_batik_pattern` | Text | `NO` | Pilih `YES`, `NO`, atau `UNSURE`. |
| `category` | Text | `TAS` | Menentukan pilihan produk. |
| `product` | Text | `TOTE_BAG` | Harus cocok dengan kategori. Jika `LAINNYA`, isi `custom_product`. |
| `quantity` | Text | `1` | Bilangan bulat 1–20. |
| `whatsapp` | Text | `+6281234567890` | Nomor seluler Indonesia. |
| `fabric_photos` | File | `denim.jpg` | Wajib 1–3 gambar, maksimal 5 MiB per gambar. Ulangi key untuk setiap file. |
| `reference_photos` | File | `referensi.jpg` | Opsional, hingga 3 gambar, maksimal 5 MiB per gambar. Saat mengedit, foto lama ikut dihitung dalam batas masing-masing jenis. |
| `fabric_condition` | Text | `LIGHT_DAMAGE` | Opsional. Pilihan lain adalah `GOOD` dan `FAIR`. |

**Aksi artisan**

| Nilai `action` | Status awal | Data tambahan | Status hasil |
| --- | --- | --- | --- |
| `review_accept` | `PENDING_REVIEW` | `notes` opsional | `AWAITING_FABRIC` |
| `review_reject` | `PENDING_REVIEW` | Alasan wajib di `notes` | `REJECTED` |
| `receive_fabric` | `AWAITING_FABRIC` | Sebelum tenggat penyerahan. `notes` opsional. | `INSPECTION` |
| `inspection_pass` | `INSPECTION` | Wajib `work_price`. Jika pengguna meminta aksen batik, isi `batik_material_price`. Jika ada biaya tambahan, kirim `additional_fee_type` dan `additional_fee_amount` bersama. | `AWAITING_APPROVAL` |
| `inspection_reject` | `INSPECTION` | Alasan kain tidak layak wajib di `notes` | `REJECTED` |
| `mark_ready` | `IN_PROGRESS` | Tanpa field tambahan | `READY` |

#### Rewards

Awalan rute adalah `/api/v1/rewards/`. Ganti `<id>` dengan ID numerik voucher katalog. [Rute](rewards/api_urls.py) · [Serializer](rewards/serializers.py)

| Metode dan rute | Akses | Body atau parameter | Respons sukses |
| --- | --- | --- | --- |
| `GET overview/` | Pengguna yang login | — | `200` · Saldo `available_points`, `lifetime_points`, progres level, hingga 5 transaksi terbaru dan 8 voucher pilihan. |
| `GET history/` | Pemilik transaksi | `type=all` (default), `in`, atau `out`. Contoh `?type=in&page=1`. | `200` · Objek `count`, `next`, `previous`, `results`, dengan 6 transaksi per halaman. |
| `GET catalog/` | Pengguna yang login | — | `200` · Array voucher aktif dengan stok, biaya poin, dan nominal diskon positif. |
| `POST catalog/<id>/redeem/` | Pengguna yang login | Tanpa body. Biaya mengikuti voucher katalog. | `201` · `redemption.voucher_code` memuat kode voucher dan `available_points` memuat sisa saldo. |
| `GET vouchers/` | Pemilik voucher | — | `200` · Array penukaran milik pengguna, termasuk `voucher_code`, `voucher_status`, `points_spent`, dan `discount_value_snapshot` saat ditukar. |
| `GET admin/vouchers/` | Staf dengan `view_reward` atau `add_reward` | — | `200` · Array voucher katalog, termasuk yang dinonaktifkan. |
| `POST admin/vouchers/` | Staf dengan `add_reward` | Contoh `{"name":"Voucher Batik","points_required":50,"stock":3,"discount_value":"15000.00"}`. Voucher aktif secara default dan memerlukan diskon positif. Gunakan multipart untuk field `image`. | `201` · Voucher baru beserta `id`. |
| `GET admin/vouchers/<id>/` | Staf dengan `view_reward`, `add_reward`, atau `change_reward` | — | `200` · Detail voucher untuk staf. |
| `PATCH admin/vouchers/<id>/` | Staf dengan `change_reward` | Kirim field yang berubah. Contoh `{"is_active":false}` untuk menonaktifkan voucher. | `200` · Detail voucher terbaru. |

#### Batas percobaan dan respons kesalahan

Kuota berikut berlaku per akun. Untuk aksi yang sama, web dan API menggunakan penghitung database yang sama. Pada respons `429`, header `Retry-After` menyatakan waktu tunggu dalam detik.

| Aksi | Batas per 60 detik | Perilaku |
| --- | --- | --- |
| Buat pengajuan upcycling | 5 percobaan | Maksimal 10 pengajuan aktif sekaligus. Jika batas jumlah pengajuan aktif tercapai, responsnya `409`. |
| Edit pengajuan upcycling | 10 percobaan | Kuota edit terpisah dari kuota buat. Pengajuan harus masih menunggu penugasan. |
| Tukar voucher | 5 percobaan | Periode dimulai pada percobaan pertama. Percobaan gagal ikut dihitung. Di web, membuka pratinjau bebas kuota dan menekan konfirmasi memakai kuota. Saat dibatasi, API mengirim JSON dengan `detail` dan web menampilkan waktu tunggu. |

| Status HTTP | Contoh penyebab | Yang diperiksa klien |
| --- | --- | --- |
| `400 Bad Request` | Field tidak valid, filter salah, poin tidak cukup, atau stok voucher habis. | Baca pesan pada nama field atau `detail`. |
| `403 Forbidden` | Sesi atau token CSRF tidak valid, atau peran tidak memiliki izin. | Periksa sesi login, header CSRF, dan izin akun. |
| `404 Not Found` | UUID pengajuan milik pengguna lain, atau ID voucher untuk penukaran tidak ditemukan atau sudah nonaktif. | Periksa ID dan akun yang sedang login. |
| `409 Conflict` | Status upcycling tidak mengizinkan aksi atau kuota pengajuan aktif tercapai. | Muat ulang detail pengajuan sebelum melanjutkan. |
| `429 Too Many Requests` | Batas percobaan aksi tercapai. | Tunggu sesuai header `Retry-After`. |

| Pengujian lokal | Perintah |
| --- | --- |
| Endpoint upcycling untuk pengguna, artisan, dan staf | `python manage.py test upcycling.tests_api -v 2` |
| Batas penukaran per akun, saldo dan stok saat ditolak, serta kedaluwarsa kuota | `python manage.py test rewards.tests_api.RewardsAPITests.test_redemption_rate_limit_is_per_user_and_expires -v 2` |
| Kuota bersama untuk konfirmasi web dan penukaran API | `python manage.py test rewards.tests_api.RewardsAPITests.test_api_and_confirmed_web_redemptions_share_one_quota -v 2` |

## Jenis/Peran Pengguna Aplikasi

1. **Guest (Pengunjung)**
   Menjelajahi Landing Page, membaca Batik Story, melihat peta Drop-Off Point, dan mengeksplorasi Marketplace.

2. **Eco-Member (Donatur & Pembeli)**
   Mengelola profil pribadi, mengajukan donasi kain/pakaian, membuat permintaan Upcycling/Custom Batik, membeli produk di Marketplace, melacak status pengiriman, serta mengumpulkan dan menukarkan Points/Reward.

3. **Artisan / Partner (Pengrajin Batik)**
   Mengajukan klaim pasokan bahan baku kain perca, mengelola pesanan Upcycling & Custom Batik, mengunggah karya ke Marketplace, dan menulis narasi pada Batik Story.

4. **Admin (Pengelola Platform)**
   Memverifikasi donasi kain masuk, memvalidasi permohonan bahan baku dari pengrajin, memoderasi produk & konten Batik Story, serta mengelola transaksi global platform.

## Link Deployment PWS

[Deployment ReBatik](https://alisa-selvia-rebatik.pws.cs.ui.ac.id/)

## Link Figma

[Desain Figma ReBatik](https://www.figma.com/team_invite/redeem/xncR93E4zlnRJtCDqu4D7p?t=LXe1ZVPkQu6McFi1-21)

## Konfigurasi environment

Jangan menyimpan `SECRET_KEY` asli atau mengaktifkan `DEBUG` di production. Untuk setup lokal:

1. Salin `.env.example` menjadi `.env`:

   **Windows PowerShell**

   ```powershell
   Copy-Item .env.example .env
   ```

   **macOS/Linux**

   ```bash
   cp .env.example .env
   ```

2. Buat kunci acak dengan perintah berikut:

   **Windows PowerShell**

   ```powershell
   python -c "import secrets; print(secrets.token_urlsafe(50))"
   ```

   **macOS/Linux**

   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(50))"
   ```

3. Buka `.env`, lalu ganti nilai pada baris `SECRET_KEY=` dengan hasil perintah tadi. Setelah itu, simpan file.
4. Gunakan `DEBUG=True` dan `PRODUCTION=False` di `.env` untuk menjalankan proyek secara lokal. Dengan `PRODUCTION=False`, database yang digunakan adalah SQLite.

File `.env` tidak dilacak Git. Jangan bagikan atau commit isi file tersebut.

### Menyiapkan Django secara lokal

Jika belum memiliki virtual environment, buat terlebih dahulu. Setelah itu aktifkan dan pasang dependency proyek:

**Windows PowerShell**

```powershell
python -m venv env
.\env\Scripts\Activate.ps1
```

**macOS/Linux**

```bash
python3 -m venv env
source env/bin/activate
```

Setelah virtual environment aktif, jalankan:

```bash
python -m pip install -r requirements.txt
python manage.py migrate
```

Jalankan `migrate` sebelum menjalankan server lokal, dan ulangi jika ada migration baru.

### Konfigurasi production di PWS

Di proyek ReBatik yang sudah ada, buka tab **Environs**, lalu atur variabel berikut. Buat `SECRET_KEY` production baru dengan perintah pembuat kunci di atas; gunakan nilai yang berbeda dari kunci lokal.

- `DEBUG=False` dan `PRODUCTION=True`.
- `DB_NAME`, `DB_HOST`, `DB_PORT`, `DB_USER`, dan `DB_PASSWORD`: gunakan kredensial database dari ITF.
- `SCHEMA=tugas_kelompok`.
- `CLOUDINARY_URL`: salin URL API dari Cloudinary Console untuk menyimpan foto unggahan. Simpan hanya di Environs PWS atau `.env` lokal; jangan commit nilainya.

Saat `PRODUCTION=True`, semua variabel database di atas, termasuk `SCHEMA`, dan `CLOUDINARY_URL` wajib diisi. Upload gambar memakai Cloudinary di production, sedangkan development lokal tetap memakai `media/`. Nilai boolean `DEBUG` dan `PRODUCTION` yang diterima adalah `true`/`false`, `1`/`0`, atau `yes`/`no` (huruf besar-kecil tidak berpengaruh).

Sebelum media lama di PWS dihapus atau tidak lagi tersedia, jalankan `python manage.py migrate_legacy_media_to_cloudinary --dry-run` untuk memeriksa file lokal lama, lalu jalankan `python manage.py migrate_legacy_media_to_cloudinary` untuk mengunggahnya dan memperbarui referensi database. Perintah migrasi berhenti tanpa mengunggah jika ada file lokal yang hilang. Jalankan saat aplikasi terhubung ke database PWS dan file lama masih tersedia di `MEDIA_ROOT`.

Pertahankan variabel PWS lain yang sudah ada, lalu simpan perubahan dengan **Update All Variables**.

Jangan membagikan nilai rahasia melalui chat atau memasukkannya ke repository. Database SQLite lokal terpisah dari PostgreSQL PWS; datanya tidak otomatis disalin saat database production disiapkan. GitHub Actions menggunakan kunci sementara khusus untuk testing dan `PRODUCTION=False`.

## Menjalankan Tailwind CSS

ReBatik menggunakan Tailwind CSS v4 untuk membantu membuat tampilan halaman. Django tetap digunakan untuk menjalankan aplikasi web, sedangkan Node.js dan npm digunakan untuk mengompilasi CSS Tailwind.

### Persiapan pertama kali

1. Tailwind CSS v4 membutuhkan Node.js versi 20 atau lebih baru. Untuk menyamakan lingkungan tim, gunakan Node.js versi 24 LTS dari [situs resmi Node.js](https://nodejs.org/en/download/). npm ikut terpasang bersama Node.js.
2. Tutup dan buka kembali terminal, lalu pastikan keduanya sudah terdeteksi:

   ```bash
   node --version
   npm --version
   ```

3. Buka terminal di folder utama ReBatik, yaitu folder yang berisi `manage.py` dan `package.json`.
4. Pasang dependency sesuai versi yang dikunci proyek:

   ```bash
   npm ci
   ```

   Perintah ini membaca `package-lock.json`. Jalankan lagi jika baru pertama kali menyiapkan proyek di komputer atau jika dependency perlu dipasang ulang. Jangan commit folder `node_modules/`.

### Mengompilasi CSS

File sumber Tailwind ada di `static/css/tailwind.input.css`. Tailwind menghasilkan file `static/css/tailwind.css`, yang dipanggil oleh `templates/base.html`. File hasil build ini diabaikan Git. Setiap anggota tim perlu membangunnya di komputer lokal, sedangkan GitHub Actions membangunnya kembali sebelum deployment ke PWS.

Untuk mengompilasi CSS satu kali setelah memasang dependency:

```bash
npm run tailwind:build
```

Jangan commit `static/css/tailwind.css` atau folder `node_modules/`. Commit perubahan pada template atau file sumber Tailwind saja.

Jika tampilan lokal belum memiliki styling setelah clone atau pull, jalankan `npm ci` lalu `npm run tailwind:build`. Karena file hasil build tidak dilacak Git, konflik pada file tersebut tidak perlu diselesaikan.

### Mengembangkan tampilan

1. Buka satu terminal di folder utama proyek dan jalankan:

   ```bash
   npm run tailwind:watch
   ```

   Biarkan perintah ini tetap berjalan. Tailwind akan membuat ulang `static/css/tailwind.css` ketika template atau file sumber berubah.

2. Buka terminal kedua di folder utama proyek, aktifkan virtual environment Python, lalu jalankan Django:

   ```bash
   python manage.py runserver
   ```

3. Buka alamat lokal yang ditampilkan Django di browser. Setelah mengubah class Tailwind di template, muat ulang halaman untuk melihat hasilnya.

Gunakan class Tailwind langsung pada elemen HTML di template Django, misalnya `class="p-4 text-lg"`. Jalankan `npm run tailwind:build` sebelum menjalankan Django jika mode watch tidak sedang berjalan. CI juga membangun CSS saat memeriksa PR.

### Deployment ke PWS

Pastikan repository GitHub memiliki secret `PWS_URL` di **Settings → Secrets and variables → Actions**. Jangan menaruh URL berkredensial di workflow atau README.

Push ke `main` menjalankan tes dan membangun Tailwind. Setelah tes lulus, workflow membuat commit deployment yang menyertakan `static/css/tailwind.css`, lalu mengirimnya ke PWS. File CSS tersebut hanya ada di riwayat PWS, bukan di GitHub. Karena itu, deploy ke PWS dilakukan melalui GitHub Actions; jangan melakukan push manual ke remote PWS.

Workflow deployment tidak menjalankan migration database production. Setelah rilis yang menambah migration tiba di PWS, jalankan `python manage.py migrate` dari console PWS dengan konfigurasi environment production, lalu pastikan migration terkait tercatat melalui `python manage.py showmigrations rewards`. Jangan menjalankan migration production dari komputer lokal karena `.env` lokal menggunakan database SQLite yang terpisah.

Sebelum merge, workflow dapat dijalankan manual dari tab **Actions**. Pemicu manual menjalankan tes, membangun CSS, lalu melakukan dry run push ke PWS. Ini memeriksa alur push tanpa memperbarui branch PWS atau melakukan deployment.

Jika PowerShell menampilkan pesan bahwa `npm` tidak bisa dijalankan karena execution policy, gunakan `npm.cmd` sebagai pengganti `npm` pada perintah di atas, misalnya `npm.cmd ci` atau `npm.cmd run tailwind:build`.

## AI Disclosure (Pengungkapan Penggunaan AI)

### 1. Alat AI yang Digunakan

Selama proses pengembangan ReBatik, tim menggunakan beberapa alat berbasis Artificial Intelligence (AI) sebagai alat bantu dalam proses perancangan, pengembangan, pemecahan masalah, dan penyusunan dokumentasi.

| Alat | Penggunaan |
|------|------------|
| **ChatGPT (OpenAI)** | Membantu memahami konsep Django, mendiskusikan struktur aplikasi, memberikan saran kode, menjelaskan implementasi Python, HTML, CSS, dan JavaScript, serta membantu menganalisis dan memperbaiki error selama pengembangan. |
| **Claude (Anthropic)** | Mengeksplorasi ide desain antarmuka (UI/UX), menyusun konsep tampilan halaman, serta memberikan saran implementasi komponen antarmuka, termasuk halaman Impact Tracker. |
| **CodeRabbit** | Digunakan secara terbatas untuk membantu proses pengujian deployment. |
| **GitHub AI** | Digunakan secara terbatas untuk membantu proses pengujian deployment. |

### 2. Bentuk Penggunaan AI dalam Pengembangan

Penggunaan AI difokuskan pada beberapa aspek pengembangan ReBatik, yaitu:

- **Perencanaan dan Desain:** Membantu mengeksplorasi ide tampilan halaman, rancangan fitur, serta alur interaksi pengguna sebelum implementasi.
- **Pengembangan Frontend:** Memberikan referensi struktur HTML, penyesuaian CSS, pengembangan layout responsif, dan interaksi menggunakan JavaScript.
- **Pengembangan Backend:** Membantu memahami dan mengimplementasikan konsep Django, termasuk Models, Forms, Views, URL Routing, serta pengelolaan data melalui database.
- **Debugging:** Membantu menganalisis pesan error, memahami traceback, mengidentifikasi kemungkinan penyebab masalah, dan memberikan alternatif penyelesaian.
- **Dokumentasi:** Membantu menyusun penjelasan teknis dan merapikan dokumentasi penggunaan aplikasi.
- **Pengujian Deployment:** CodeRabbit dan GitHub AI hanya digunakan untuk membantu proses pengujian deployment, dan tidak digunakan untuk menulis kode atau fitur aplikasi.

### 3. Strategi Penyusunan Prompt

Dalam menggunakan AI, tim menerapkan pendekatan bertahap dan iteratif. AI tidak hanya diberikan instruksi umum untuk membuat keseluruhan aplikasi, tetapi juga diberikan konteks dan permasalahan yang lebih spesifik.

Tahapan yang dilakukan meliputi:

1. Menjelaskan kebutuhan fitur, tujuan implementasi, dan hasil yang diharapkan.
2. Memberikan konteks berupa potongan kode, struktur folder proyek, tangkapan layar desain, atau pesan error yang ditemukan.
3. Meminta saran, penjelasan, atau alternatif penyelesaian sesuai permasalahan yang sedang dihadapi.
4. Meninjau dan menyesuaikan hasil yang diberikan agar sesuai dengan struktur aplikasi ReBatik yang sudah ada.
5. Melakukan pengujian dan perbaikan secara bertahap apabila implementasi belum berjalan sesuai harapan.

Prompt juga disesuaikan kembali berdasarkan hasil implementasi, terutama ketika saran yang diberikan belum sesuai dengan kebutuhan atau struktur proyek.

### 4. Keterbatasan AI dan Penyesuaian Manual

Hasil yang diberikan AI tidak selalu dapat langsung diterapkan. Beberapa saran memerlukan penyesuaian karena AI tidak selalu memiliki konteks lengkap mengenai struktur proyek, konfigurasi, dependensi, dan implementasi yang telah dibuat sebelumnya.

Beberapa keterbatasan yang ditemukan selama pengembangan antara lain:

- **Integrasi Proyek:** Saran kode terkadang menggunakan nama fungsi, import, URL, atau lokasi template yang berbeda dari struktur aplikasi yang sebenarnya. Oleh karena itu, diperlukan penyesuaian secara manual.
- **Styling Frontend:** Beberapa saran CSS tidak langsung sesuai dengan stylesheet dan konfigurasi Tailwind CSS yang digunakan. Tim perlu memeriksa kembali pemanggilan stylesheet, selector, serta hasil kompilasi CSS.
- **Database dan Migration:** Perubahan pada model memerlukan pemeriksaan migration agar struktur database tetap sesuai dengan implementasi model terbaru.
- **Integrasi JavaScript dan HTML:** Penggunaan ID elemen, selector, dan event handler perlu disesuaikan dengan struktur HTML yang sebenarnya agar interaksi berjalan dengan baik.
- **Proses Debugging:** Solusi yang diberikan AI tidak selalu langsung menyelesaikan masalah. Beberapa error memerlukan pemeriksaan tambahan terhadap kode dan konfigurasi proyek.

Oleh karena itu, setiap saran yang diperoleh dari AI ditinjau dan disesuaikan kembali oleh tim. Keputusan akhir terkait implementasi, integrasi, dan perbaikan tetap menjadi tanggung jawab tim pengembang.

### 5. Verifikasi dan Pengujian

Implementasi yang memperoleh bantuan AI diperiksa dan diuji kembali dalam lingkungan pengembangan lokal sebelum digunakan sebagai bagian dari aplikasi ReBatik.

Proses verifikasi meliputi:

- Menjalankan pemeriksaan aplikasi menggunakan `python manage.py check`.
- Menjalankan migration ketika terdapat perubahan pada model database.
- Menguji pengiriman form dan memastikan data berhasil tersimpan ke database.
- Memeriksa URL routing dan proses rendering template.
- Memeriksa tampilan frontend, termasuk pemanggilan CSS dan interaksi JavaScript.
- Menguji integrasi setiap fitur dengan aplikasi ReBatik secara keseluruhan.

### 6. Transparansi dan Tanggung Jawab Pengembangan

AI digunakan sebagai alat bantu selama proses pengembangan, bukan sebagai pengganti pemahaman dan tanggung jawab tim.

Tim tetap bertanggung jawab dalam meninjau, menyesuaikan, mengintegrasikan, serta menguji hasil implementasi sebelum digunakan dalam aplikasi. Seluruh keputusan akhir mengenai fungsionalitas, desain, dan integrasi kode berada di bawah tanggung jawab tim pengembang.
