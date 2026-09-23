# PRD — Masa Depan Jakarta (MDJ) Scholarship Portal

## Problem Statement
Portal beasiswa MDJ BAZNAS (BAZIS) Provinsi DKI Jakarta untuk pendaftaran mahasiswa,
verifikasi panitia, pengelolaan penerima manfaat, pencairan, dan konten publik.

## Architecture
- **Backend**: FastAPI + MongoDB (Motor). Semua rute memakai prefiks `/api`.
- **Frontend**: React 19 + React Router 7 + Tailwind + shadcn + sonner.
- **Auth**: JWT email/kata sandi serta OAuth Google terkelola; peran student, admin,
  admin_wilayah, dan super_admin.
- **Storage**: Emergent Object Storage untuk dokumen mahasiswa dan aset CMS.

## User Personas
1. **Mahasiswa** — mendaftar, mengisi profil, unggah berkas, mengikuti seleksi.
2. **Admin Provinsi** — menilai peserta dan mengelola operasional tingkat DKI.
3. **Admin Wilayah** — mengakses data sesuai cakupan wilayah.
4. **Super Admin** — mengelola seluruh akun administrasi dan konten situs.

## Core Requirements
- Beranda publik berbasis CMS, termasuk berita dan kategori berita.
- Pendaftaran mahasiswa, profil, dokumen, pakta integritas, dan pelacakan status.
- Dashboard serta workflow verifikasi bagi Admin.
- CMS penuh untuk Super Admin, termasuk kategori berita yang digunakan konsisten oleh
  editor berita dan halaman `/berita`.
- Operasional penerima manfaat, surat aktif, pencairan, audit, dan komunikasi.

## Current Status (2026-09)
- **P0 selesai**: kategori Berita sekarang dikelola Super Admin melalui Kelola Website.
  Kontrol tambah, ubah, dan hapus berada di bagian atas tab **Pengumuman**, tanpa tab terpisah.
- Setiap pengumuman memiliki pilihan **Popup Akun Mahasiswa** dan **Popup Beranda**.
  Masing-masing tujuan dibatasi satu popup aktif dan popup hanya tampil sekali setelah ditutup.
- Banner popup mengikuti rasio asli dan tampil penuh tanpa pemotongan gambar.
- Kartu berita pada Beranda hanya menampilkan satu tautan detail **Baca Selengkapnya**.
- Tanggal pengumuman dibuat otomatis dalam format Indonesia dan tidak dapat diedit dari CMS.
- Super Admin dapat mengatur kuota penerima; kartu status Beranda menampilkan kuota serta
  tanggal bulan penuh atau singkat sesuai ruang yang tersedia.
- Tombol Kembali ke Beranda pada login berada di kanan atas panel formulir.
- Alamat email Hubungi Kami pada footer tampil satu baris dengan ukuran responsif tanpa overflow.
- Footer menyediakan tautan WhatsApp langsung untuk Hotline Kampus dan Hotline Mahasiswa.
- Footer desktop memakai kolom kontak yang lebih lebar; hotline dan email tampil satu baris dalam
  ukuran teks normal, tanpa nomor telepon BAZNAS.
- Alur Pendaftaran kini dikelola penuh dari CMS dan ditampilkan sebagai pola zig-zag adaptif untuk
  jumlah tahap berapa pun.
- Ikon sosial footer mengarah ke akun Instagram MDJ, YouTube BAZNAS BAZIS, dan Facebook BAZNAS
  BAZIS resmi.
- Bagian Tentang tidak lagi menampilkan gambar stok saat refresh; hanya gambar dari CMS yang
  dirender setelah data tersedia.
- Kartu status pendaftaran Beranda menggunakan judul Masa Depan Jakarta Scholarship Tahun 2027
  serta keterangan ajakan pendaftaran terbaru.
- Profil Mahasiswa memiliki tab Keluarga dengan data Ayah, Ibu, anggota keluarga lain dinamis,
  daya listrik rumah, format Rupiah, dan validasi wajib di server.
- Super Admin dapat mengimpor peserta dari XLSX berformat sendiri melalui pemetaan kolom, dengan
  status Lolos / Penerima tanpa berkas dan pembaruan otomatis untuk duplikat.
- Data Peserta Super Admin mendukung tambah pendaftar manual serta penghapusan permanen satu
  pendaftar, satu kampus, atau seluruh pendaftar dengan dialog konfirmasi.
- Impor peserta dapat membuat master Kampus beserta Nama Bank, Nomor Rekening, dan Pemilik
  Rekening; konflik rekening dilaporkan tanpa menimpa data kampus.
- Akun demo mahasiswa `mahasiswa.mdj@baznasbazisdki.id` terlindungi dari hapus tunggal, per
  kampus, maupun seluruh peserta; tabel Data Peserta menampilkan label **Akun Demo** dan ikon
  hapus nonaktif.
- Akun demo dikecualikan dari daftar, statistik, dan proses operasional Penerima Manfaat.
- Data Peserta kini memuat profil, akun, dan jumlah dokumen secara batch untuk mempercepat
  pencarian dan tampilan daftar peserta.
- Dialog Hapus Data membuka pencarian satu peserta secara default; Super Admin dapat mencari
  nama, email, atau kampus, memilih tepat satu hasil, lalu meninjau data sebelum hapus permanen.
- Seluruh dashboard akun memiliki kontrol **Tutup sidebar** berbasis ikon. Mode ringkas hanya
  menampilkan ikon dengan tooltip, tersedia di desktop maupun ponsel, dan kembali terbuka saat
  halaman dimuat ulang atau pengguna login lagi. Saat melebar, kontrol tutup dan keluar tersusun
  berdampingan tanpa scrollbar horizontal di atas kontrol buka, dengan tombol Keluar di kiri dan
  ikon Tutup Sidebar di kanan.
- Kelola Website kini memiliki tab **Footer & Kontak** untuk mengatur tautan Facebook, Instagram,
  YouTube, tautan sosial tambahan, judul Hubungi Kami, serta daftar kontak dinamis beserta aksi
  tautannya.
- Referensi implementasi historis dipindahkan ke [`CHANGELOG.md`](CHANGELOG.md).
- Prioritas selanjutnya tercatat di [`ROADMAP.md`](ROADMAP.md).

## Test Credentials
Rujuk `/app/memory/test_credentials.md`.
