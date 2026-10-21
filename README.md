# ReBatik ꕥꕥ

ReBatik adalah platform yang menghadirkan konsep upcycling dengan mengolah pakaian dan kain yang sudah tidak terpakai menjadi karya baru melalui sentuhan seni dan budaya batik Nusantara. Dengan memadukan kreativitas dan warisan budaya Indonesia, ReBatik menghadirkan karya yang tidak hanya ramah lingkungan, tetapi juga memiliki nilai estetika, budaya, dan ekonomis.

## Nama Anggota Kelompok 1 PBP-D

1. Ahyan Timuardi (2506547203)
2. Alisa Selvia Saharani (2506618433)
3. Ausy Dhafa Adhitama (2406417954)
4. M. Rezky Syahputra (2506614006)
5. Rani Faizah A (2506624013)

## Daftar Modul Beserta Deskripsi dan Pembagian

### Modul 1: Landing Page
**Deskripsi:** Menjelaskan masalah limbah tekstil serta konsep ReBatik Impact Tracker yang menunjukkan jumlah kain yang berhasil dialihkan dari limbah.

**Penanggung Jawab:** Ausy Dhafa Adhitama

### Modul 2: Batik Custom
**Deskripsi:** User dapat memilih motif/jenis produk atau mengajukan desain Batik Story. Modul ini juga menampilkan informasi mengenai motif dan filosofi batik yang digunakan.

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

## Sumber/Dokumentasi Public API

- **Circularity API**  
  Digunakan sebagai referensi data terkait circular economy dan pengelolaan limbah tekstil.  
  https://circularity.id/

- **Batik API**  
  Digunakan untuk memperoleh data terkait batik, motif, atau informasi budaya batik.  
  https://batikita.docs.apiary.io/#

- **Alamat API**  
  Digunakan untuk memperoleh data alamat/lokasi yang mendukung fitur Drop-Off Point.  
  https://alamat.thecloudalert.com/

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

File sumber Tailwind ada di `static/css/tailwind.input.css`. Tailwind menghasilkan file `static/css/tailwind.css`, yang sudah dipanggil oleh `templates/base.html`. File hasil build ini sengaja disimpan di Git agar tersedia saat aplikasi dijalankan dan di-deploy.

Untuk mengompilasi CSS satu kali, misalnya sebelum commit:

```bash
npm run tailwind:build
```

Simpan perubahan pada `static/css/tailwind.css` bersama perubahan tampilan yang menggunakannya. Jangan masukkan `node_modules/` ke commit.

Jika terjadi konflik Git pada `static/css/tailwind.css`, selesaikan konflik terlebih dahulu pada template Django atau file sumber CSS. Setelah sumbernya beres, jalankan ulang `npm run tailwind:build`, lalu stage dan commit hasil `static/css/tailwind.css` yang baru. Jangan menyelesaikan konflik dengan mengedit file hasil build secara manual.

### Mengembangkan tampilan

1. Buka satu terminal di folder utama proyek dan jalankan:

   ```bash
   npm run tailwind:watch
   ```

   Biarkan perintah ini tetap berjalan. Tailwind akan membuat ulang `static/css/tailwind.css` ketika file sumber berubah.

2. Buka terminal kedua di folder utama proyek, aktifkan virtual environment Python, lalu jalankan Django:

   ```bash
   python manage.py runserver
   ```

3. Buka alamat lokal yang ditampilkan Django di browser. Setelah mengubah class Tailwind di template, muat ulang halaman untuk melihat hasilnya.

Gunakan class Tailwind langsung pada elemen HTML di template Django, misalnya `class="p-4 text-lg"`. Jika mengubah `tailwind.input.css` atau class pada template, jalankan `npm run tailwind:build` sebelum commit bila mode watch tidak sedang berjalan.

Jika PowerShell menampilkan pesan bahwa `npm` tidak bisa dijalankan karena execution policy, gunakan `npm.cmd` sebagai pengganti `npm` pada perintah di atas, misalnya `npm.cmd ci` atau `npm.cmd run tailwind:build`.
