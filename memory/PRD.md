# PRD — Masa Depan Jakarta (MDJ) Scholarship Portal

## Problem Statement
Complete a full-stack scholarship registration portal for BAZNAS (BAZIS) Provinsi DKI Jakarta from an attached React mockup. Three roles: Mahasiswa (student pendaftar), Admin Pendaftaran MDJ (manages registered participants), Super Admin (manages registrants, creates admin accounts, manages website content — banner, timeline, announcements, FAQ, statistics, requirements, registration period).

## Architecture
- **Backend**: FastAPI + MongoDB (motor). All routes under `/api`.
- **Frontend**: React 19 + React Router 7 + Tailwind + shadcn + recharts + sonner. Fonts: Outfit (display), Plus Jakarta Sans (body). Identity: green #27AE60 / dark #0B6B3A / gold #F2C94C.
- **Auth**: Dual — JWT email/password (httpOnly cookie + Bearer token) AND Emergent-managed Google login. Roles: student, admin, super_admin.
- **Storage**: Emergent object storage for student documents & site banner (real integration).

## User Personas
1. Mahasiswa — registers, completes profile, uploads docs, submits registration, tracks selection status.
2. Admin Pendaftaran — reviews participants, views documents, updates selection status.
3. Super Admin — all admin abilities + creates/manages admin accounts + edits all public website content.

## Core Requirements (static)
- Public landing page with dynamic content.
- Student self-registration + profile + document upload + registration submit + status tracker.
- Admin participant management with status workflow.
- Super admin user management + full CMS for site content.

## Implemented (2026-06)
- Public landing page (hero, stats, about, categories, requirements, timeline, announcements, FAQ, CTA, footer) driven by GET /api/site/content.
- Auth: register/login/logout/me, Google session exchange, super admin seeding (supri@baznasbazisdki.id).
- Student dashboard: ringkasan, profile (pribadi/alamat/pendidikan) with completion %, registration (draft/submit), document upload grid (9 doc types, replace/delete), selection status stepper + history, announcements, settings.
- Admin dashboard: stats overview (tiles + trend chart), participants table (filter/search), detail modal (profile+docs+account), status update.
- Super admin dashboard: stats, participants, admin account CRUD (create/toggle/delete with guards), website CMS (banner upload, period/status, hero text, timeline, announcements, statistics, requirements, FAQ editors).
- Role-based routing & backend role gating (verified). 34/34 backend tests pass.
- Landing page CTA dan footer diperbarui mengikuti referensi visual: CTA hijau dengan dua aksi,
  footer gelap empat kolom, tautan sosial, legal, kontak, dan baris hak cipta responsif.
- Halaman login diperbarui sesuai referensi visual: panel informasi hijau, formulir putih,
  input email/NIK, kontrol visibilitas kata sandi, ingat saya, dan Google login.
- Akun demo otomatis untuk mahasiswa dan admin ditambahkan di startup; seluruh tiga peran telah
  diverifikasi melalui API dan antarmuka (100% pengujian login lulus).
- Login kini menyediakan tombol akun demo sekali klik untuk Super Admin, Admin/PIC, dan Mahasiswa.
  Setiap tombol kini menjalankan login normal dan mengarahkan pengguna ke dashboard perannya.
- Bug akun demo yang hanya menampilkan notifikasi telah diperbaiki dan diverifikasi end-to-end:
  Super Admin ke `/super-admin`, Admin/PIC ke `/admin`, dan Mahasiswa ke `/dashboard`.
- Halaman Profil Saya (student) diredesain sesuai referensi: header badge "Calon Penerima Manfaat" +
  persentase kelengkapan, indikator langkah, sub-tab (Data Pribadi | Alamat | Data Pendidikan | Foto Profil),
  field baru "Status Perkawinan", Informasi Kontak dengan badge email Terverifikasi. Komponen baru
  `/app/frontend/src/components/StudentProfile.jsx`.
- Fitur AI "Isi Otomatis dari KTP": unggah JPG/PNG/WEBP/PDF KTP → Gemini 3.1 Pro (gemini-3.1-pro-preview via
  Emergent LLM Key) mengekstrak & mengisi otomatis Nama, NIK, Tempat/Tgl Lahir (dinormalisasi YYYY-MM-DD),
  Jenis Kelamin (L/P), Agama, Status Perkawinan, dan Alamat (RT/RW/kel/kec/kota/provinsi). Endpoint
  `POST /api/profile/extract-ktp`. Data hasil AI tetap dapat diedit. Diverifikasi end-to-end (curl + UI).
- Tab Pengaturan (student) diredesain: panel "Informasi Akun" (Email + badge Terverifikasi, Nomor Telepon +
  badge status) dan "Keamanan Akun" (ganti kata sandi + indikator kekuatan). Komponen
  `/app/frontend/src/components/AccountSettings.jsx` + halaman `/verify-email` (`VerifyEmail.jsx`).
  - Ganti kata sandi: `POST /api/auth/change-password` (verifikasi kata sandi lama, min 8 char). Terverifikasi.
  - Ubah email dengan link verifikasi via Emergent Resend: `POST /api/auth/email/change-request` →
    email berisi tautan → `POST /api/auth/email/verify`. Token 1 jam, sekali pakai. Terverifikasi end-to-end.
  - Ubah nomor via OTP SMS (Twilio Verify): `POST /api/auth/phone/send-otp` & `/verify-otp`.
    CATATAN: fitur SMS AKTIF hanya setelah kredensial Twilio (TWILIO_ACCOUNT_SID/AUTH_TOKEN/VERIFY_SERVICE_SID)
    diisi di backend/.env. Saat ini kosong → endpoint mengembalikan 503 "Verifikasi SMS belum dikonfigurasi".
- Struktur navigasi mahasiswa disederhanakan: menu **Dokumen** di sidebar dihapus. Menu **Pendaftaran** kini
  memiliki submenu **Formulir**, **Data Pendidikan**, dan **Dokumen**. Data Pendidikan dipindahkan dari Profil
  Saya; unggah, ganti, dan hapus dokumen tetap menggunakan alur API dokumen yang sama.

## Backlog / Remaining
- **P1**: Forgot/reset password flow; brute-force lockout on login.
- **P1**: Restrict GET /api/files to owner + admins (defense-in-depth).
- **P2**: Email notifications on status change (Resend).
- **P2**: Export participants to Excel/CSV.
- **P2**: Restrict CORS_ORIGINS to frontend origin.

## Test Credentials
See /app/memory/test_credentials.md. Demo mahasiswa, admin, dan super admin tersedia otomatis.


## 2026-06 — Scan AI Kartu Keluarga
- Endpoint `POST /api/profile/extract-kk` (Gemini 3.1 Pro, mengembalikan `noKK` saja sesuai pilihan user).
- Kartu 'Isi Otomatis dari Kartu Keluarga' di tab Data Pribadi, di bawah kartu KTP (`DocScanUploader` generik di StudentProfile.jsx). Tested via curl + screenshot.

## 2026-06 — Auto-simpan file scan KTP/KK
- `extract-ktp`/`extract-kk` kini juga menyimpan file ke Object Storage + `documents` (doc_type "KTP DKI Jakarta"/"Kartu Keluarga (KK)", mengganti dokumen lama). Response berisi `document`.
- Kartu scan di Profil menampilkan "Dokumen tersimpan: <nama file>"; daftar Dokumen Pendaftaran ikut terupdate. Tested via curl + screenshot.

## 2026-06 — Kompresi banner + pratinjau dokumen
- `POST /api/site/banner` kini kompres gambar via Pillow (maks lebar 1600px, JPEG q72). Object store menolak WebP → gunakan JPEG.
- `GET /api/files/{path}`: file site (banner) publik tanpa auth + Cache-Control immutable; dokumen mahasiswa tetap butuh auth.
- Landing: HERO_IMG default diperkecil (w=1600,q=60), fallback onError, bg solid saat loading.
- `DocPreview.jsx`: modal pratinjau gambar/PDF (iframe). Dipakai di tab Dokumen (klik nama file), kartu scan KTP/KK, dan foto profil.
- Catatan: banner saat ini adalah gambar uji acak (banner_91c6425b.jpg) — user perlu unggah ulang banner asli.

## 2026-09 — Kualitas kompresi unggahan disesuaikan
- Dokumen mahasiswa (KTP, KK, pas foto, dan unggahan lain) kini memakai batas lebar 2400px
  dan JPEG kualitas 86, sehingga teks identitas lebih tajam tanpa menghilangkan penghematan ukuran.
- Banner memakai batas lebar 1920px dan JPEG kualitas 80 untuk menjaga ketajaman visual hero.
- Kompresi hanya dipakai apabila hasil akhirnya lebih kecil daripada file asli.
- Diuji: unggahan PNG 3200px menjadi JPEG 323.054 byte dari 415.656 byte dan tulisan tetap
  terbaca jelas pada pratinjau Admin Pendaftaran. Penanda menu desktop/mobile juga dibuat unik.

## 2026-09 — Pembaruan visual laman depan
- Gambar bagian Tentang Program diganti dengan kolase kegiatan dan prestasi MDJ yang diunggah pengguna.
- Banner hero dipulihkan ke gambar sebelumnya sesuai klarifikasi pengguna.
- CMS Super Admin kini mendukung unggah ulang Gambar Tentang Program melalui endpoint
  `POST /api/site/about-image`; kedua gambar disimpan di Object Storage dan ditampilkan publik.
- Diuji: API CMS serta laman publik memuat gambar Tentang yang baru dan banner hero yang dipulihkan.

## 2026-09 — Scan AI dokumen pendidikan
- Tab Data Pendidikan kini menyediakan unggah dan pemindaian AI untuk KTM serta KRS/KHS/Transkrip Nilai.
- Hasil scan mengisi kolom pendidikan yang dapat diedit: perguruan tinggi, NIM, program studi,
  jenjang, semester, dan IPK; file juga otomatis tersimpan di daftar Dokumen.
- Endpoint baru: `POST /api/profile/extract-ktm` dan
  `POST /api/profile/extract-academic-record` menggunakan Gemini 3.1 Pro.
- Diuji menyeluruh: 5/5 backend lulus, alur browser lulus, data tetap tersimpan setelah reload,
  pratinjau dokumen bekerja, serta tampilan mobile tidak mengalami horizontal overflow.

## 2026-09 — Logo MDJ di header laman depan
- Ikon topi pada header landing page diganti dengan logo MDJ Scholarship yang diunggah pengguna.
- Logo disimpan sebagai aset CMS publik melalui endpoint `POST /api/site/logo` dan dapat diperbarui
  kembali oleh Super Admin di menu Umum & Banner.
- Diuji: logo CMS tampil pada header beranda dan gambar tersimpan tetap menjaga detail lambang.

## 2026-09 — Perapian kartu unggah KTP dan KK
- Kartu scan AI KTP dan Kartu Keluarga memakai tata letak fleksibel dengan tombol unggah yang
  konsisten di sisi kanan pada layar desktop.
- Informasi hasil scan dan tautan dokumen tersimpan tetap berada rapi pada area konten kiri.
- Diuji melalui browser: kedua tombol unggah berada sejajar di sisi kanan tanpa overflow.

## 2026-09 — Indikator kelengkapan berkas dashboard
- Ringkasan mahasiswa kini menampilkan persentase kelengkapan berkas pada kartu statistik,
  beserta hitungan dokumen yang sudah diunggah.
- Panel Kelengkapan Pendaftaran kini memiliki progress bar terpisah untuk Profil dan Berkas.
- Perhitungan hanya menggunakan 10 jenis berkas persyaratan resmi dan diperbarui setelah unggah/hapus.
- Diuji melalui browser: akun demo menampilkan 20% untuk 2 dari 10 berkas yang telah diunggah.

## 2026-09 — Urutan tab Pendaftaran
- Tab Pendaftaran diurutkan menjadi **Data Pendidikan**, **Dokumen**, lalu
  **Formulir Pakta Integritas**.
- Data Pendidikan menjadi tab awal saat mahasiswa membuka menu Pendaftaran.
- Diuji melalui browser: urutan dan tab aktif awal sesuai arahan pengguna.

## 2026-09 — Nominal biaya pendidikan per semester
- Data Pendidikan kini memiliki kolom **Nominal Biaya Pendidikan / Semester** dengan awalan Rp
  dan pemisah ribuan otomatis.
- Nilai disimpan sebagai angka pada data profil dan dapat diperbarui melalui tombol Simpan Data Pendidikan.
- Diuji melalui browser: Rp 3.500.000 tersimpan dan tetap tampil benar setelah halaman dimuat ulang.

## 2026-09 — Avatar dari pas foto mahasiswa
- Pas foto yang diunggah pada Profil Saya kini otomatis menjadi avatar mahasiswa di header dashboard.
- Avatar mengambil file privat melalui URL bertoken; inisial nama tetap muncul sebagai cadangan bila foto gagal dimuat.
- Diuji melalui browser: foto profil tersimpan dimuat sebagai avatar pada sudut kanan atas dashboard.

## 2026-09 — Notifikasi mahasiswa
- Lonceng pada header mahasiswa kini menampilkan notifikasi tersimpan untuk progres seleksi dan
  pengumuman baru dari Admin/Super Admin.
- Admin yang mengubah status peserta otomatis mengirim notifikasi ke peserta terkait; pengumuman baru
  dari CMS otomatis dikirim ke seluruh mahasiswa yang memiliki pendaftaran.
- Mahasiswa dapat membuka detail, menandai satu notifikasi atau seluruhnya sebagai sudah dibaca;
  daftar diperbarui kembali setiap 30 detik.
- Diuji menyeluruh: 6/6 pengujian backend lulus, popover, titik belum dibaca, akses per pengguna,
  tautan ke menu relevan, dan tampilan mobile seluruhnya terverifikasi.

## 2026-09 — Dashboard tahapan seleksi Admin
- Menu Ringkasan akun Admin diganti menjadi **Dashboard** untuk memantau tahapan penerimaan Calon
  Penerima Manfaat, dari pendaftaran terkirim hingga penerima manfaat/lulus.
- Dashboard menampilkan total pendaftar, mahasiswa dalam proses, total mahasiswa lulus, cakupan
  wilayah lulusan, tingkat kelulusan keseluruhan, serta grafik kelulusan menurut kota/kabupaten.
- Endpoint `GET /api/admin/stats` kini mengembalikan `passed_by_region` dari data profil pendaftar.
- Diuji menyeluruh: 4/4 backend lulus; enam tahap, data wilayah, keadaan kosong, dan tampilan mobile
  telah diverifikasi tanpa overflow.

## 2026-09 — Pemisahan Dashboard dan Ringkasan Admin
- Sidebar Admin kini memiliki urutan **Dashboard → Ringkasan → Data Peserta → Kampus**; Ringkasan
  menjadi halaman awal Admin saat login.
- **Dashboard** khusus menampilkan penerima manfaat yang berstatus Lolos seluruh tahap, total penerima,
  cakupan wilayah, serta infografis dan daftar penerima manfaat per wilayah.
- **Ringkasan** menampilkan jumlah peserta mendaftar dari awal, pendaftaran terkirim, proses seleksi,
  pengumuman aktif, enam tahap proses hingga pengumuman penerima, dan grafik proses seleksi.
- Ringkasan memiliki filter Keseluruhan Wilayah atau wilayah tertentu. Diuji menyeluruh: 4/4 backend,
  kedua menu, filter, kondisi kosong, dan tampilan mobile lulus tanpa overflow.

## 2026-09 — Data kampus dan data peserta Admin
- Admin/Super Admin dapat mengimpor XLSX, menambah, mengubah, dan menghapus kampus; 377 kampus dari
  lampiran telah diimpor. Mahasiswa dapat memilih Kampus Lainnya yang kemudian mendapat kode otomatis.
- Tabel Data Peserta kini memiliki nomor urut, total mahasiswa, kolom Wilayah, serta filter keseluruhan
  atau enam wilayah DKI; opsi Belum diisi dihapus dari filter.
- Sebanyak 50 mahasiswa data uji telah dibuat dari kampus terdaftar dan tersebar di enam wilayah DKI,
  dengan 12 penerima manfaat lulusan untuk mengisi grafik Dashboard. Semua ditandai Data Uji MDJ.
- Diuji menyeluruh: 10/10 backend dan 8/8 alur Data Peserta lulus, termasuk filter wilayah serta mobile.
