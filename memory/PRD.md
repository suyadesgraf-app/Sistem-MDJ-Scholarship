# PRD — Masa Depan Jakarta (MDJ) Scholarship Portal

## Problem Statement
Complete a full-stack scholarship registration portal for BAZNAS (BAZIS) Provinsi DKI Jakarta from an attached React mockup. Three roles: Mahasiswa (student pendaftar), Admin Pendaftaran MDJ (manages registered participants), Super Admin (manages registrants, creates admin accounts, manages website content — banner, timeline, announcements, FAQ, statistics, requirements, registration period).

## Architecture
- **Backend**: FastAPI + MongoDB (motor). All routes under `/api`.
- **Frontend**: React 19 + React Router 7 + Tailwind + shadcn + recharts + sonner. Fonts: Outfit (display), Plus Jakarta Sans (body). Identity: green #27AE60 / dark #0B6B3A / gold #F2C94C.
- **Auth**: Dual — JWT email/password (httpOnly cookie + Bearer token) AND Emergent-managed Google login. Roles: student, admin (Admin Provinsi), admin_wilayah, super_admin.
- **Storage**: Emergent object storage for student documents & site banner (real integration).

## User Personas
1. Mahasiswa — registers, completes profile, uploads docs, submits registration, tracks selection status.
2. Admin Provinsi — reviews all participants, manages Admin Wilayah, Penerima Manfaat, dan pencairan.
3. Admin Wilayah — manages existing selection scope and reads Penerima Manfaat untuk wilayahnya saja.
4. Super Admin — all admin abilities + creates/manages all admin accounts + edits all public website content.

## Core Requirements (static)
- Public landing page with dynamic content.
- Student self-registration + profile + document upload + registration submit + status tracker.
- Admin participant management with status workflow.
- Super admin user management + full CMS for site content.
- Kelola Data PM untuk penerima berstatus lulus akhir, surat aktif, pencairan, dan audit.

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
- **P1**: Brute-force lockout on login.
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

## 2026-09 — Penyatuan logo resmi MDJ
- Logo resmi Masa Depan Jakarta Scholarship yang diunggah pengguna disimpan ulang pada CMS sebagai
  sumber merek tunggal.
- Header beranda dan sidebar seluruh dashboard kini memuat logo resmi yang sama, menggantikan ikon topi
  wisuda yang sebelumnya dipakai sebagai identitas merek.
- Diuji melalui browser: URL logo beranda dan sidebar Admin identik serta gambar tampil dengan benar.

## 2026-09 — Akses login dari navigasi dan hero beranda
- Tombol kanan atas navigasi desktop dan mobile kembali menjadi **Masuk** dan membuka halaman `/login`.
- Tombol utama **Daftar Beasiswa** pada hero juga membuka halaman Login yang berisi pilihan akun demo
  dengan pengisian otomatis.
- Diuji melalui browser: kedua tombol membuka halaman Login yang sama dan daftar akun demo tersedia.

## 2026-09 — Penyamaan alur tombol pendaftaran
- Arah tombol hero diperbarui sesuai klarifikasi pengguna: tombol hero dan navigasi sama-sama mengarah
  ke halaman Login, bukan ke formulir pendaftaran langsung.

## 2026-09 — Ekspor data peserta Excel
- Admin dapat mengekspor Data Peserta ke XLSX yang mengikuti pencarian, status, dan filter wilayah aktif.
- XLSX memuat seluruh data tabel, ID CPM, kontak, serta data pendidikan lengkap: NIM, jurusan, semester,
  IPK, dan biaya pendidikan per semester.
- Diuji testing agent: 5/5 backend dan alur unduhan browser lulus; XLSX valid, filter diterapkan, dan
  akses mahasiswa ditolak dengan benar.
- Google Spreadsheet langsung ditunda sesuai arahan pengguna hingga `GOOGLE_CLIENT_ID` dan
  `GOOGLE_CLIENT_SECRET` OAuth diberikan untuk akun `pendaftaranmdj@baznasbazisdki.id`.

## 2026-09 — Import hasil wawancara dan kelulusan
- Menu **Import Seleksi** menerima XLSX fleksibel untuk hasil Lolos Wawancara dan Kelulusan Akhir,
  menyimpan berkas audit privat, serta memperbarui status peserta yang cocok secara aman.
- Pencocokan memakai urutan ID CPM → NIK → email → nama, kampus, dan wilayah. Data baru, data tanpa
  identitas, atau data tidak sesuai tidak mengubah status dan dipisahkan dalam daftar tinjauan.
- Gemini 3.1 Pro membantu memetakan header sumber dan memberi catatan bagi data janggal; Admin dapat
  menghapus item dari daftar tinjauan serta mengunduh berkas import dari riwayat.
- Diuji testing agent: 8/8 backend dan alur UI lulus, termasuk status wawancara/kelulusan, notifikasi,
  unduhan audit, karantina data, RBAC, serta pembersihan data uji.

## 2026-09 — Verifikasi Administrasi berbantuan AI
- Menu **Verifikasi AI** tersedia bagi Admin dan Super Admin untuk memeriksa peserta berstatus Terkirim
  atau Verifikasi Administrasi.
- Pemeriksaan mencakup seluruh 10 berkas, seluruh data profil wajib, kampus pada master kampus, NIK 16
  digit, NIM, IPK, serta biaya pendidikan per semester. Gemini 3.1 Pro memberi rekomendasi konservatif.
- Admin dapat menyetujui rekomendasi satu per satu atau seluruhnya melalui dialog konfirmasi; hanya saat
  disetujui status berubah menjadi Lolos Administrasi dan mahasiswa menerima notifikasi.
- Diuji testing agent: 6/6 backend lulus, akses student ditolak, rekomendasi lengkap/kurang tepat,
  persetujuan terpilih/massal berhasil, mobile tidak overflow, dan seluruh data uji sementara dibersihkan.

## 2026-09 — Contoh rekomendasi AI
- Lima mahasiswa contoh berlabel **Contoh Rekomendasi AI 01–05** ditambahkan sebagai data uji permanen
  untuk memperlihatkan hasil rekomendasi Verifikasi AI.
- Masing-masing memiliki profil pendidikan lengkap, 10 berkas metadata, kampus terdaftar, dan status
  Terkirim; Gemini 3.1 Pro merekomendasikan kelimanya untuk Lolos Administrasi.
- Status kelima contoh tetap Terkirim hingga Admin menyetujui secara eksplisit melalui halaman Verifikasi AI.

## 2026-09 — Favicon logo resmi MDJ
- Favicon menggunakan aset logo resmi MDJ pada `/favicon.png` melalui `frontend/public/index.html`.
- Layanan frontend dimuat ulang agar template HTML terbaru digunakan.
- Diuji pada browser: elemen favicon ditemukan dan aset PNG dimuat dari URL publik dengan HTTP 200.

## 2026-09 — Admin Wilayah dengan akses terlingkup
- Role baru `admin_wilayah` mewajibkan satu dari enam wilayah DKI: Jakarta Pusat, Utara, Barat,
  Selatan, Timur, atau Kepulauan Seribu.
- Admin/PIC Provinsi serta Super Admin dapat membuat dan mengelola Admin Wilayah; Admin/PIC hanya
  dapat mengelola akun regional, sedangkan Super Admin tetap dapat mengelola seluruh jenis akun.
- Admin Wilayah dibatasi di server pada peserta, detail, pembaruan status, statistik, ekspor Excel,
  verifikasi AI, dan impor seleksi. Upaya membuka atau mengubah peserta wilayah lain menghasilkan 404.
- Dashboard Admin Wilayah tidak memuat menu Kampus atau pengelolaan akun dan menampilkan indikator
  wilayah kerja. Form Admin/PIC mewajibkan pemilihan wilayah saat membuat akun regional.
- Diuji menyeluruh: 19/19 test backend lulus, pemeriksaan UI Admin/PIC dan Admin Wilayah lulus,
  serta layar 390px tanpa horizontal overflow. Suite regresi: `backend/tests/test_admin_wilayah.py`.

## 2026-09 — Admin Provinsi dan Kelola Data PM
- Sebutan Admin/PIC di login, dashboard, daftar akun, serta formulir kini menjadi **Admin Provinsi**.
  Role `admin` tetap sama secara teknis agar akun lama mempertahankan cakupan DKI penuh.
- Hanya Super Admin dapat membuat Admin Provinsi atau Super Admin. Admin Provinsi hanya dapat
  membuat dan mengelola Admin Wilayah.
- Menu **Kelola Data PM** tersedia bagi Super Admin, Admin Provinsi, dan Admin Wilayah dalam mode
  baca-saja terlingkup. Daftar mengambil registrasi berstatus `lolos` dan memuat NIM, kampus,
  wilayah, surat aktif, serta status pencairan Tahap I dan Tahap II.
- Admin Provinsi/Super Admin dapat mengunggah sampai 20 PDF/JPG/JPEG/PNG surat aktif atau bukti
  transfer per proses. Gemini 3.1 Pro membaca banyak mahasiswa/transaksi; pencocokan otomatis
  mewajibkan nama dan NIM yang tepat, sementara data kosong/ganda/tidak cocok masuk tinjauan.
- Setiap tahap pencairan memiliki status, nominal, tanggal, referensi, catatan, serta bukti terkait.
  Nomor rekening tersimpan terenkripsi dan hanya ditampilkan tersamarkan; hasil OCR rekening hanya
  menjadi penanda sesuai/tidak sesuai/perlu tinjau, bukan persetujuan otomatis.
- Dokumen sumber, pemetaan, perubahan rekening/pencairan, penyelesaian tinjauan, dan unduhan dicatat
  pada audit. Admin Wilayah tidak dapat mengubah data, mengunggah, melihat antrean tinjauan, atau
  mengunduh sumber mentah.
- Diuji menyeluruh: 30/30 backend dan semua pemeriksaan UI lulus, termasuk RBAC, validasi magic byte,
  masking rekening, pencairan, filter wilayah, dashboard, serta mobile 390px tanpa overflow.

## 2026-09 — Pencairan Dana berbasis kampus
- Menu **Kelola Data PM** diganti menjadi **Pencairan Dana**. Halaman utama kini memiliki satu baris
  per kampus, dengan nomor urut, total penerima lulus akhir, jumlah wilayah, status Tahap I/II, dan
  jumlah bukti transfer yang tertaut.
- Rincian kampus membagi data menurut wilayah. Setiap kombinasi kampus + wilayah + tahap memiliki
  status, nominal kolektif, tanggal, referensi, catatan, bukti, transaksi cocok, dan daftar mahasiswa.
- Bukti transfer sumber disimpan sekali, tetapi dapat dihubungkan ke beberapa agregat kampus/wilayah
  berdasarkan nama kampus, nomor rekening kampus, serta atas nama rekening. Hasil tanpa kecocokan
  yang cukup tetap berada di tinjauan.
- Admin Wilayah hanya melihat kampus dan mahasiswa wilayahnya; semua mutasi, unggahan, pemetaan,
  serta unduhan sumber tetap ditolak di server. Admin Provinsi dan Super Admin mengelola agregat.
- Kontrol unggah surat keterangan mahasiswa aktif dihapus dari halaman Pencairan Dana agar fokus
  operasional hanya pada pencairan dan bukti transfer. Endpoint surat aktif sebelumnya tetap ada.
- Diuji menyeluruh: 19/19 pengujian agregat kampus dan 30/30 regresi PM lulus. Uji tampilan terbaru
  mengonfirmasi nomor urut berurutan, tombol surat aktif tidak tampil, dan layar 390px tanpa overflow.

## 2026-09 — Pengelolaan Pencairan per Tahap
- **Tahap I** menjadi tampilan awal. Kontrol tahap utama mengganti seluruh konteks halaman ke Tahap I
  atau Tahap II, termasuk kartu ringkasan, tabel kampus, jumlah bukti, tombol unggah, rincian kampus,
  formulir pengelolaan, riwayat, dan antrean tinjauan.
- Tabel hanya memperlihatkan status serta bukti pada tahap aktif. Rincian setiap wilayah hanya memiliki
  satu panel tahap aktif sehingga data Tahap I dan Tahap II tidak lagi tampil berdampingan.
- Tombol unggah selalu mengirimkan tahap yang dipilih. Endpoint tinjauan dan riwayat menerima parameter
  `stage` tervalidasi (`1` atau `2`) agar data antar tahap tidak tercampur.
- Admin Wilayah tetap hanya membaca tahap aktif untuk wilayahnya sendiri; unggahan, simpan, serta
  pemetaan tetap tidak tersedia dan ditolak di server.
- Diuji menyeluruh: 58/58 pengujian backend lulus; default Tahap I, perpindahan konteks Tahap II,
  isolasi data antar tahap, read-only regional, nomor urut, dan layar mobile 390px semuanya lulus.

## 2026-09 — Wilayah wajib untuk unggah bukti transfer
- Admin Provinsi/Super Admin wajib memilih salah satu wilayah DKI sebelum membuka unggahan bukti
  transfer. Server menolak wilayah kosong, tidak valid, maupun format yang tidak persis cocok sebelum
  proses OCR dimulai.
- Wilayah pilihan disimpan sebagai `selected_region` pada sumber bukti dan masuk ke konteks OCR.
  Pencocokan deterministik kampus/rekening hanya mempertimbangkan Penerima Manfaat lulus akhir dari
  wilayah tersebut; transaksi wilayah lain masuk tinjauan.
- Pemilihan wilayah unggahan otomatis menyaring ringkasan, tabel kampus, filter wilayah, dan antrean
  tinjauan di bawahnya. Indikator halaman menyebutkan wilayah yang sedang ditampilkan.
- Penyelesaian tinjauan juga dikunci: bukti berwilayah tidak dapat dipetakan manual ke mahasiswa dari
  wilayah lain. Pilihan penerima di antrean tinjauan hanya memperlihatkan kandidat wilayah unggahan.
- Diuji: 71/71 regresi backend lulus untuk validasi wilayah, pembatasan Admin Wilayah, dan guard
  pemetaan lintas wilayah. Browser mengonfirmasi pilihan Jakarta Utara langsung menyaring data kampus
  serta layar 390px tanpa overflow.

## 2026-09 — Master rekening kampus dan data demo bukti transfer
- Master Kampus kini menyimpan **atas nama rekening** serta nomor rekening kampus terenkripsi.
  Nomor penuh tidak pernah dikirim ke browser; admin hanya melihat nomor tersamarkan.
- OCR bukti transfer tidak lagi memakai nama atau NIM mahasiswa. Pencocokan otomatis memerlukan
  nama kampus, nomor rekening tujuan, dan atas nama rekening yang cocok pada master kampus, lalu
  hanya memproses Penerima Manfaat di wilayah unggahan.
- Tiga contoh bukti transfer digunakan sebagai data demo acuan: 24 master `DEMO-TF` dan 24 Penerima
  Manfaat demo berstatus lulus akhir pada Jakarta Utara (18), Jakarta Pusat (4), dan Jakarta Timur (2).
  Berkas sumber tidak diunggah otomatis sehingga tetap dapat dipakai untuk uji unggahan manual.

## 2026-09 — Surat Aktif AI dengan persetujuan eksplisit
- Menu **Surat Aktif AI** untuk Admin Provinsi dan Super Admin memiliki dua proses: Verifikasi Faktual
  serta kelayakan Pencairan Tahap II. AI mengidentifikasi kampus dan tabel mahasiswa, membuat
  rekomendasi/karantina, dan tidak mengubah status secara otomatis.
- Persetujuan Verifikasi Faktual mengubah peserta wawancara menjadi lulus; persetujuan Tahap II hanya
  membuat catatan kelayakan Tahap II. Seluruh keputusan, notifikasi, dan audit dicatat.
- Persetujuan massal kini wajib dibatasi oleh workflow dan daftar source ID unggahan yang tampil.
  Rekomendasi berkas lain serta kandidat yang statusnya telah berubah tidak dapat ikut terproses.
- Delapan kandidat demo Universitas Muhammadiyah Tangerang dari surat contoh dipertahankan dalam
  status `wawancara` untuk pengujian manual.

## 2026-09 — Format rekap PDF dan Bukti TF mahasiswa
- Tabel Pencairan Dana mengikuti format rekap: nomor, perguruan tinggi, jumlah/nama mahasiswa,
  nominal pengajuan, waktu transfer, nominal transfer, Bukti TF, keterangan, dan rincian.
- Setiap bukti yang terhubung tampil sebagai **Bukti TF 1/2/3** dengan ikon mata untuk meninjau berkas.
  Penerima manfaat yang tercakup memperoleh notifikasi dan dapat membuka bukti TF miliknya melalui
  menu Bukti Transfer pada dashboard mahasiswa; akses dibatasi ke bukti yang memang tertaut kepadanya.
- Keterangan otomatis memuat kekurangan atau kelebihan transfer. Selisih positif hingga Rp101 dianggap
  kode unik dan tetap dinilai sesuai. Perubahan manual menambahkan penanda “Data diedit oleh Admin”
  serta catatan operator bila ada.
- Diuji menyeluruh: 92/92 regresi backend lulus, termasuk pemulihan delapan demo UMT, scope persetujuan
  massal, nominal/remark, bukti mahasiswa, RBAC, data demo, dan format tabel. Tampilan rekap desktop
  serta mobile 390px juga diverifikasi tanpa overflow.

## 2026-09 — Alur Pendaftaran interaktif dan CMS
- Bagian **Alur Pendaftaran** baru di beranda menampilkan 11 tahap tetap dari Pembuatan Akun hingga
  Pencairan Bantuan Tahap II. Kartu memiliki nomor dan panah berurutan; hover/fokus di desktop atau
  ketukan di ponsel menampilkan keterangan tahap pada panel penuh di bawah alur.
- Super Admin dapat mengisi keterangan untuk masing-masing dari 11 tahap melalui Kelola Website →
  Alur Pendaftaran. Judul serta urutan tahap dilindungi di server sehingga tidak dapat diubah atau
  dikurangi melalui pembaruan CMS.
- Diuji menyeluruh: 100% backend dan frontend lulus, termasuk 11 kartu, 10 panah, hover/fokus,
  ketukan mobile, anchor navigasi, editor CMS, validasi 11 tahap, dan layar mobile tanpa overflow.

## 2026-09 — Navigasi Beranda, Masuk, dan Daftar
- Tombol **Daftar** hijau ditambahkan kembali pada header beranda untuk desktop maupun menu ponsel
  dan mengarah ke halaman pembuatan akun.
- Halaman Masuk serta Daftar kini selalu menampilkan tombol **Kembali ke Beranda**, termasuk pada
  layar desktop.
- Diuji di browser: seluruh navigasi Beranda/Daftar berfungsi dan tampilan ponsel 390px tidak overflow.

## 2026-09 — Dropdown keterangan Alur Pendaftaran
- Keterangan alur tidak lagi tampil sebagai panel global di bawah seluruh rangkaian. Pada desktop,
  dropdown kini muncul tepat di bawah kartu tahap yang sedang diarahkan kursor atau menerima fokus.
- Saat pengguna mengarahkan kursor ke tahap lain, dropdown sebelumnya tertutup dan keterangan tahap
  baru terbuka. Di ponsel, satu dropdown tahap aktif tetap terbuka secara otomatis dan berubah saat
  kartu disentuh.
- Diuji di browser: dropdown awal desktop tersembunyi, posisi dropdown berada di bawah kartu,
  perpindahan antar tahap benar, dan mobile 390px tidak mengalami horizontal overflow.

## 2026-09 — Urutan zig-zag Alur Pendaftaran
- Alur desktop kini mengikuti pola proses visual: **01 → 02 → 03**, turun ke **04 ← 05 ← 06**,
  turun ke **07 → 08 → 09**, lalu turun ke **11 ← 10**. Panah berubah arah mengikuti alurnya.
- Tampilan ponsel tetap vertikal 01 sampai 11 agar mudah dibaca dan disentuh, tanpa mengubah urutan
  proses sebenarnya.
- Diuji di browser: posisi setiap kartu dan arah urutan desktop tervalidasi; dropdown hover tetap
  berfungsi dan layar mobile 390px tidak mengalami horizontal overflow.

## 2026-09 — Pembuatan akun tanpa NIK
- Input NIK dihapus dari halaman **Buat Akun Pendaftar** beserta state dan payload registrasinya.
  Pembuatan akun sekarang hanya meminta nama lengkap, email, nomor telepon, dan kata sandi.
- Data NIK pada profil mahasiswa tetap terpisah untuk proses dokumen/identitas setelah akun dibuat.
- Diuji di browser: input NIK tidak lagi ada pada halaman Daftar dan layar mobile 390px tanpa overflow.

## 2026-09 — Subteks menyatu pada kartu Alur Pendaftaran
- Saat tahap Alur Pendaftaran aktif, subteks kini melebar di dalam kartu yang sama tepat di bawah judul
  alur. Label “Keterangan Tahap 01” dan seterusnya dihapus agar tampil lebih ringkas.
- Hover/fokus desktop dan ketukan ponsel tetap mengaktifkan subteks pada kartu terkait; kontras subteks
  diperkuat menjadi putih penuh agar jelas terbaca pada latar hijau.
- Diuji di browser: subteks berada di dalam batas kartu aktif, label lama tidak muncul, dan layar ponsel
  tetap responsif tanpa horizontal overflow.

## 2026-09 — Lupa Sandi dan pengaturan ulang kata sandi
- Tautan **Lupa kata sandi?** pada halaman Masuk kini membuka dialog email dan mengirim permintaan ke
  `POST /api/auth/forgot-password`. Rute publik `/reset-password` menampilkan formulir kata sandi baru.
- Token reset disimpan sebagai hash, hanya berlaku satu jam dan sekali pakai. Permintaan reset baru
  membatalkan token sebelumnya; pengubahan kata sandi menaikkan `auth_version` serta membatalkan semua
  sesi aktif lama. Pembatasan permintaan per email/IP juga diperbaiki agar operasi MongoDB atomik.
- Diuji: pengiriman email Resend HTTP 200, reset berhasil melalui browser, token ulang ditolak, sesi serta
  sandi lama ditolak, sandi baru dapat masuk. Dialog desktop dan ponsel 390px lulus tanpa overflow.

## 2026-09 — Pencarian pemilihan kampus
- Pemilihan **Perguruan Tinggi** pada Data Pendidikan kini menggunakan daftar yang dapat dicari menurut
  nama atau kode kampus. Hasil pilihan langsung mengisi data institusi seperti sebelumnya.
- Opsi **Kampus Lainnya** dipisahkan dari area daftar yang dapat digulir sehingga selalu melekat dan
  tersedia, termasuk saat hasil pencarian kosong.
- Diuji melalui browser desktop dan ponsel 390px: pencarian, pemilihan kampus, Kampus Lainnya, serta
  input nama kampus manual berfungsi tanpa horizontal overflow. Build frontend lulus.

## 2026-09 — Broadcast Pengumuman Hasil Seleksi Berkas
- Admin Provinsi dan Super Admin kini memiliki menu **Pengumuman Seleksi** untuk memilih Semua Kategori
  atau satu kategori, melihat ringkasan mahasiswa lulus/tidak lulus, lalu mengonfirmasi publikasi massal.
- Broadcast menyimpan kampanye `selection_announcements` dengan `status_publikasi: Published`, menandai
  registrasi penerima dengan `is_announcement_published`, serta membuat notifikasi hasil unik per mahasiswa.
  Admin Wilayah dan mahasiswa ditolak di server.
- Setelah login, mahasiswa yang memiliki hasil baru menerima pop-up **Pengumuman Hasil Seleksi Berkas**.
  CTA menampilkan hasil LULUS bertema hijau atau TIDAK LULUS bertema netral-merah beserta arahan. Setiap
  penerima menyimpan `is_read` dan `is_popup_seen`, sehingga pop-up tidak muncul lagi setelah selesai.
- Diuji testing agent: 11/11 backend dan alur Admin/Mahasiswa desktop-mobile lulus, termasuk broadcast per
  kategori, RBAC, pemisahan antar pengguna, hasil lulus/tidak lulus, pembacaan, pencegahan broadcast ulang,
  serta pembersihan data uji. Suite: `backend/tests/test_selection_announcement_broadcast.py`.

## 2026-09 — Menu Bukti Transfer mahasiswa disembunyikan
- Item sidebar **Bukti Transfer** disembunyikan dari tampilan desktop dan ponsel akun mahasiswa.
- Modul, data, dan jalur internal Bukti Transfer tidak dihapus sehingga dapat dimunculkan kembali saat diminta.
- Diuji di browser pada desktop serta layar 390px: menu tidak tampil, sementara Status Seleksi, Pengumuman,
  dan Pengaturan tetap tersedia tanpa overflow. Build frontend lulus.
