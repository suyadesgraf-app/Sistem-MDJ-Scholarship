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
- Referensi implementasi historis dipindahkan ke [`CHANGELOG.md`](CHANGELOG.md).
- Prioritas selanjutnya tercatat di [`ROADMAP.md`](ROADMAP.md).

## Test Credentials
Rujuk `/app/memory/test_credentials.md`.
