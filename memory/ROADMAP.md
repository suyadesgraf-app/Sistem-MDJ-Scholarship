# ROADMAP — MDJ Scholarship Portal

## P0 — Selesai
- Kategori Berita dinamis: CMS Super Admin, dropdown kategori pada editor berita, dan
  filter kategori publik pada `/berita`; kontrol CMS menyatu di tab Pengumuman.
- Popup pengumuman terkendali untuk akun Mahasiswa dan Beranda, dengan satu popup aktif per
  tujuan dan penyimpanan status tampil sekali.
- Perlindungan akun demo mahasiswa dari penghapusan serta pengecualian dari seluruh rekap
  Penerima Manfaat.
- CMS Footer & Kontak untuk tautan sosial serta informasi Hubungi Kami dinamis.
- Pencarian satu peserta pada dialog Hapus Data, dengan pratinjau sebelum hapus permanen.

## P1 — Ditunda sesuai arahan pengguna
- Refactor bertahap `/app/backend/server.py` yang sangat besar menjadi router/service
  terpisah tanpa mengubah kontrak API atau perilaku aplikasi.
- Brute-force lockout untuk login.
- Batasi `GET /api/files` kepada pemilik berkas dan admin sebagai pertahanan tambahan.

## P2 — Tertunda / Backlog
- Perbaiki 15 kampus pada batch data uji `PDF-JB-TAHAP1-2026` yang belum tersambung.
- Integrasi Google Sheets setelah kredensial OAuth tersedia.
- Konfigurasi SMS Twilio setelah kredensial pengguna tersedia.
- Notifikasi email perubahan status dan pembatasan CORS ke origin frontend.

## Next Action
Menunggu arahan fitur berikutnya. Refactor backend dan seluruh integrasi eksternal tetap ditunda
sesuai keputusan pengguna.
