# ReBatik ꕥꕥ

ReBatik adalah platform yang menghadirkan konsep upcycling dengan mengolah pakaian dan kain yang sudah tidak terpakai menjadi karya baru melalui sentuhan seni dan budaya batik Nusantara. Dengan memadukan kreativitas dan warisan budaya Indonesia, ReBatik menghadirkan karya yang tidak hanya ramah lingkungan, tetapi juga memiliki nilai estetika, budaya, dan ekonomis.

## Nama Anggota Kelompok 1 PBP-D

1. Ahyan Timuardi (2506547203)
2. Alisa Selvia Saharani (2506618433)
3. Ausy Dhafa Adhitama (2406417954)
4. M. Rezky Syahputra (2506614006)
5. Rani Faizah A (2506624013)

## Daftar Modul Beserta Deskripsi dan Pembagian

### Modul 1: Landing Page & Impact Tracker
**Deskripsi:** Informasi limbah tekstil, konsep ReBatik, statistik kain yang dialihkan dari limbah

**Penanggung Jawab:** Ausy Dhafa Adhitama

### Modul 2: Batik Custom & Batik Story 
**Deskripsi:** Pemilihan motif/produk batik, pengajuan desain Batik Story, filosofi motif

**Penanggung Jawab:** Alisa Selvia Saharani

### Modul 3: Marketplace & Drop-Off Point
**Deskripsi:** Menampilkan produk hasil upcycling yang dapat dibeli serta lokasi pengumpulan kain.

**Penanggung Jawab:** Ahyan Timuardi

### Modul 4: Donasi Kain/Pakaian & Profile
**Deskripsi:** User dapat mengunggah kain atau pakaian yang sudah tidak digunakan. Profile menampilkan riwayat donasi, pesanan, dan kontribusi user.

**Penanggung Jawab:** Rani Faizah A

### Modul 5: Upcycling Request & Points/Reward
**Deskripsi:** User dapat memilih kainnya ingin diolah menjadi produk apa dan mendapatkan poin dari aktivitas menyumbangkan kain.

**Penanggung Jawab:** M. Rezky Syahputra

## Sumber/Dokumentasi API

### Public API

| Layanan | Endpoint / Metode | Kegunaan | Dokumentasi |
|---|---|---|---|
| API Wilayah Indonesia (emsifa) | `GET https://www.emsifa.com/api-wilayah-indonesia/v2/provinces.json`<br>`GET https://www.emsifa.com/api-wilayah-indonesia/v2/regencies/{province_id}.json`<br>`GET https://www.emsifa.com/api-wilayah-indonesia/v2/districts/{regency_id}.json`<br>`GET https://www.emsifa.com/api-wilayah-indonesia/v2/villages/{district_id}.json` | Dropdown provinsi sampai kelurahan beserta kode pos pada form alamat (Drop-Off Point, Donasi, Upcycling Request). Ganti placeholder ID dengan ID wilayah yang dipilih. | [Dokumentasi emsifa](https://www.emsifa.com/api-wilayah-indonesia/)|

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
- `CLOUDINARY_URL`: salin nilai URL API dari Cloudinary Console untuk menyimpan foto unggahan. Simpan hanya di Environs PWS atau `.env` lokal; jangan commit nilainya.

Saat `PRODUCTION=True`, semua variabel database di atas, termasuk `SCHEMA`, dan `CLOUDINARY_URL` wajib diisi. Upload gambar memakai Cloudinary di production, sedangkan development lokal tetap memakai `media/`. Nilai boolean `DEBUG` dan `PRODUCTION` yang diterima adalah `true`/`false`, `1`/`0`, atau `yes`/`no` (huruf besar-kecil tidak berpengaruh).

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

Sebelum merge, workflow dapat dijalankan manual dari tab **Actions**. Pemicu manual menjalankan tes, membangun CSS, lalu melakukan dry run push ke PWS. Ini memeriksa alur push tanpa memperbarui branch PWS atau melakukan deployment.

Jika PowerShell menampilkan pesan bahwa `npm` tidak bisa dijalankan karena execution policy, gunakan `npm.cmd` sebagai pengganti `npm` pada perintah di atas, misalnya `npm.cmd ci` atau `npm.cmd run tailwind:build`.
