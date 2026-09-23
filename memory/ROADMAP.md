# ROADMAP — MDJ Scholarship Portal

## P0 — Selesai
- Kategori Berita dinamis: CMS Super Admin, dropdown kategori pada editor berita, dan
  filter kategori publik pada `/berita`; kontrol CMS menyatu di tab Pengumuman.

## P1 — Prioritas Berikutnya
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
Mulai refactor backend secara bertahap, dimulai dengan memindahkan modul CMS/site content
dari `server.py` sambil menjaga seluruh endpoint dan pengujian tetap lulus.
