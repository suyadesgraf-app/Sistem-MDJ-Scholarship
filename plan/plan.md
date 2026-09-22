# Proposal — Akses Menu Pendaftaran Berdasarkan Periode

## Tujuan
Menghubungkan menu **Pendaftaran** pada akun mahasiswa dengan pengaturan **Periode & Status
Pendaftaran** yang dikelola Super Admin.

## Perilaku yang akan diterapkan

1. Menu **Pendaftaran** tetap terlihat di sidebar mahasiswa agar calon pendaftar mengetahui
   lokasi layanan tersebut.
2. Saat status pendaftaran dibuka oleh Super Admin, mahasiswa dapat membuka menu Pendaftaran
   dan menggunakan formulir, data pendidikan, serta dokumen seperti biasa.
3. Saat status pendaftaran belum dibuka atau sudah ditutup, klik menu Pendaftaran akan
   menampilkan pemberitahuan yang jelas:
   **"Masa pendaftaran belum dibuka. Silakan pantau pengumuman MDJ Scholarship secara berkala."**
4. Dalam status tertutup, isi formulir, unggahan dokumen, dan pengiriman pendaftaran tidak dapat
   diakses melalui menu tersebut.
5. Perubahan status oleh Super Admin berlaku langsung untuk mahasiswa yang masuk setelahnya dan
   saat mahasiswa berpindah ke menu Pendaftaran.
6. Data pendaftaran atau draf yang sudah ada tidak dihapus ketika periode ditutup; data hanya
   tidak dapat dibuka dari menu Pendaftaran sampai periode dibuka kembali.

## Keputusan yang dapat ditinjau

- Pemberitahuan akan memakai dialog ringkas dengan tombol **Tutup**, bukan mengarahkan mahasiswa
  ke halaman lain.
- Pesan menggunakan frasa **belum dibuka** untuk semua kondisi nonaktif, termasuk setelah periode
  ditutup, agar instruksi bagi mahasiswa tetap sederhana.
- Menu lain seperti Ringkasan, Profil Saya, Status Seleksi, Pengumuman, dan Pengaturan tidak
  terpengaruh.

## Hasil yang diharapkan

- Super Admin cukup mengubah status periode yang sudah tersedia untuk membuka atau menutup akses.
- Mahasiswa tidak dapat melewati aturan dengan membuka menu Pendaftaran ketika periode nonaktif.
- Saat periode aktif, seluruh alur Pendaftaran tetap berjalan tanpa perubahan pengalaman pengguna.
# Rencana — Simpan Kode Sistem MDJ Scholarship ke GitHub

## Tujuan
Menyimpan versi aplikasi Sistem MDJ Scholarship yang saat ini berjalan ke repositori:
`https://github.com/suyadesgraf-app/Sistem-MDJ-Scholarship.git`

## Cakupan
- Mengirim seluruh kode aplikasi saat ini, termasuk perubahan terbaru pada alur pendaftaran,
  pengelolaan pencairan dana, Master Kampus, dan dashboard peran.
- Menjaga file konfigurasi rahasia dan kredensial agar tidak ikut dipublikasikan.
- Menyimpan perubahan sebagai pembaruan terstruktur pada repositori tujuan.

## Asumsi
- Repositori tersebut adalah milik Anda dan menjadi tujuan utama penyimpanan kode.
- Versi aplikasi saat ini adalah versi yang ingin disimpan.
- Pembaruan dilakukan pada cabang utama repositori tanpa menghapus riwayat versi yang sudah ada.

# Rencana — Pengelolaan Pencairan per Tahap

## Perilaku halaman
- Halaman **Pencairan Dana** tetap menampilkan ringkasan per kampus dan wilayah.
- Pemilihan **Tahap I** atau **Tahap II** menjadi kontrol utama halaman, bukan sekadar pilihan
  pada tombol unggah.
- Saat **Tahap I** dipilih, tabel, rincian kampus, formulir status, nominal, referensi, catatan,
  bukti transfer, dan daftar tinjauan hanya menampilkan data Tahap I.
- Saat **Tahap II** dipilih, area yang sama hanya menampilkan proses dan data Tahap II.
- Dua tahap tidak lagi ditampilkan berdampingan pada rincian kampus.

## Unggah dan pengelolaan data
- Tombol unggah mengikuti tahap aktif: **Unggah Bukti Transfer Tahap I** atau **Unggah Bukti
  Transfer Tahap II**.
- Bukti yang diunggah hanya diproses dan ditautkan ke agregat kampus + wilayah pada tahap yang
  sedang aktif.
- Perubahan status, nominal kolektif, tanggal, nomor referensi, dan catatan hanya berlaku pada
  tahap aktif; data tahap lain tidak ditampilkan atau diubah.
- Daftar tinjauan menampilkan item bukti transfer untuk tahap aktif agar pemetaan mahasiswa tidak
  tercampur antar tahap.

## Tampilan rincian kampus
- Membuka kampus memperlihatkan wilayah dan daftar penerima seperti sekarang.
- Setiap wilayah hanya memiliki satu panel pengelolaan untuk tahap yang dipilih.
- Label, status, jumlah bukti, riwayat, dan tombol simpan menggunakan nama tahap aktif secara
  konsisten.

## Hak akses
- Admin Provinsi dan Super Admin dapat mengunggah serta mengubah data pada tahap aktif.
- Admin Wilayah tetap hanya membaca data tahap aktif di wilayahnya sendiri, tanpa tombol unggah,
  simpan, atau pemetaan.

## Asumsi
- Tahap I dipilih sebagai tampilan awal saat halaman dibuka.
- Data Tahap I dan Tahap II yang sudah tersimpan tetap dipertahankan sepenuhnya; perubahan ini
  hanya memisahkan cara melihat dan mengelolanya.
# Rencana — Pencairan Dana Berbasis Kampus

## Tujuan
Mengganti menu **Kelola Data PM** menjadi **Pencairan Dana**. Fokus halaman bergeser dari
daftar mahasiswa per orang menjadi ringkasan pencairan per kampus, dengan rincian wilayah dan
tahap dana.

## Tampilan utama Pencairan Dana
- Menu sidebar, judul halaman, dan penanda navigasi menggunakan nama **Pencairan Dana**.
- Tabel utama menampilkan satu baris per kampus, bukan satu baris per mahasiswa.
- Setiap kampus menampilkan jumlah Penerima Manfaat, jumlah wilayah yang memiliki penerima,
  status Tahap I, status Tahap II, serta jumlah bukti transfer yang sudah terhubung.
- Pencarian kampus dan filter wilayah tetap tersedia.
- Membuka satu kampus menampilkan rincian per wilayah: jumlah mahasiswa, daftar mahasiswa
  penerima, status Tahap I dan Tahap II, nilai pencairan, referensi, serta bukti transfer.

## Dasar jumlah mahasiswa
- Jumlah mahasiswa pada kampus dihitung dari Penerima Manfaat yang sudah **lulus tahap akhir**.
- Mahasiswa yang belum lulus akhir tidak ikut masuk ke total pencairan kampus.
- Data mahasiswa individual tetap dipertahankan sebagai dasar pencocokan AI dan dapat dilihat
  dari rincian kampus; tidak ada data PM yang dihapus.

## Bukti transfer berbasis kampus dan wilayah
- Admin Provinsi dan Super Admin dapat mengunggah PDF, JPG, JPEG, atau PNG bukti transfer untuk
  Tahap I atau Tahap II.
- AI membaca transaksi pada satu bukti, lalu mencocokkan nama dan NIM mahasiswa dengan data PM.
  Kampus dan wilayah diisi otomatis dari data mahasiswa yang sudah cocok.
- Satu bukti transfer dapat dihubungkan ke banyak kampus, banyak mahasiswa, dan banyak wilayah.
- Satu kampus yang memiliki mahasiswa di enam wilayah akan memiliki enam catatan pencairan pada
  Tahap I: satu catatan per wilayah. Bukti transfer yang sama dapat terpasang pada semua catatan
  wilayah yang cocok.
- Jika satu transaksi hanya dapat dikenali pada level kampus tetapi wilayahnya tidak cukup jelas,
  atau nama/NIM tidak cocok, transaksi masuk daftar tinjauan dan tidak mengubah status pencairan.

## Status dan persetujuan
- Status Tahap I dan Tahap II tetap dicatat terpisah untuk setiap kombinasi kampus dan wilayah.
- AI hanya mengisi hasil pembacaan, transaksi yang cocok, rekening tersamarkan, nominal, tanggal,
  serta referensi bila terbaca.
- AI tidak dapat menyetujui atau mencairkan dana. Perubahan status tetap dilakukan secara sadar
  oleh Admin Provinsi atau Super Admin.
- Riwayat unggah, pembacaan AI, pemetaan transaksi, perubahan status, dan unduhan bukti tetap
  dapat ditelusuri.

## Hak akses
- Super Admin dan Admin Provinsi dapat mengunggah bukti transfer, memetakan item tinjauan, dan
  memperbarui pencairan seluruh kampus/wilayah.
- Admin Wilayah hanya melihat hasil Pencairan Dana untuk kampus dan mahasiswa di wilayahnya.
  Admin Wilayah tidak dapat mengunggah, mengubah status, memetakan transaksi, atau mengunduh
  bukti sumber mentah.

## Asumsi yang digunakan
- Istilah “mahasiswa yang terdaftar pada kampus” pada halaman Pencairan Dana berarti mahasiswa
  penerima manfaat yang telah lulus tahap akhir, karena hanya mereka yang berhak diproses untuk
  pencairan.
- Satu catatan pencairan dikelompokkan berdasarkan **kampus + wilayah + tahap**. Nominal dan status
  pada catatan ini dapat mewakili pencairan kolektif untuk semua mahasiswa penerima di kombinasi
  tersebut.
- Bukti transfer massal tetap dapat disimpan sekali dan dirujuk oleh lebih dari satu catatan
  kampus/wilayah/tahap tanpa menduplikasi berkas.
# Rencana: Admin Provinsi dan Kelola Data PM

## Penamaan dan kewenangan admin
- Semua sebutan **Admin/PIC** akan berubah menjadi **Admin Provinsi** pada login, dashboard,
  daftar akun, dan formulir pembuatan akun.
- Admin Provinsi mengelola data seluruh wilayah DKI Jakarta dan dapat membuat atau mengelola
  Admin Wilayah.
- Hanya Super Admin yang dapat membuat Admin Provinsi. Admin Provinsi tidak dapat membuat
  Admin Provinsi lain atau Super Admin.
- Super Admin tetap dapat membuat dan mengelola seluruh jenis akun admin.
- Admin Wilayah tetap memiliki akses berdasarkan wilayahnya, tetapi hanya untuk melihat hasil
  Data PM wilayahnya dan tidak dapat mengubah data, mengunggah berkas, atau memproses pencairan.

## Menu Kelola Data PM
- Menu baru **Kelola Data PM** tersedia untuk Admin Provinsi dan Super Admin.
- Daftar berisi mahasiswa yang telah berstatus lulus tahap akhir sebagai Penerima Manfaat Masa
  Depan Jakarta Scholarship, lengkap dengan identitas, NIM, kampus, wilayah, dokumen aktif,
  serta ringkasan pencairan Tahap I dan Tahap II.
- Admin Wilayah menerima tampilan hasil baca-saja untuk Penerima Manfaat di wilayahnya sendiri.

## Pencairan dana Tahap I dan Tahap II
- Setiap mahasiswa memiliki pencatatan terpisah untuk Tahap I dan Tahap II.
- Setiap tahap memuat status, nominal, tanggal pencairan, nomor referensi, catatan, dan bukti
  transfer.
- Bukti transfer dapat diunggah dan dibaca AI. Hasil menampilkan nomor rekening sebagai prioritas,
  berikut nomor referensi, nominal, dan tanggal bila terbaca.
- Satu bukti transfer dapat memuat beberapa transaksi atau menjadi bukti pencairan untuk beberapa
  Penerima Manfaat. Sistem akan menyimpan rincian tiap transaksi dan menandai kecocokannya pada
  penerima terkait; transaksi yang tidak dapat dipetakan masuk ke daftar tinjauan.
- AI hanya memberi hasil verifikasi dan penanda perlu tinjau; status pencairan tetap diputuskan
  oleh Admin Provinsi atau Super Admin.

## Import surat keterangan mahasiswa aktif
- Admin Provinsi dan Super Admin dapat mengimpor satu atau banyak berkas PDF, JPG, JPEG, atau PNG.
- Satu surat dapat berisi beberapa mahasiswa. AI membaca nama dan NIM setiap mahasiswa yang tercantum.
- Sistem otomatis menempelkan surat yang sama ke setiap Penerima Manfaat yang memiliki kecocokan
  nama dan NIM serta telah lulus tahap akhir.
- Data yang tidak cocok, ganda, atau tidak lengkap masuk ke daftar tinjauan dan tidak ditempelkan
  otomatis.
- Surat yang berhasil cocok dapat menjadi lampiran bagi beberapa mahasiswa sekaligus.

## Format contoh yang sudah diperhitungkan
- Contoh surat kampus berbentuk surat jawaban verifikasi dengan tabel banyak mahasiswa. AI akan
  mengenali baris Nama, NIM, Program Studi, dan Semester, lalu memakai Nama dan NIM untuk pencocokan.
- Contoh bukti transfer berbentuk ringkasan transfer massal dengan beberapa transaksi. AI akan
  mengenali status transaksi, tanggal, nominal total dan per transaksi, nomor referensi, nama
  rekening kredit, serta nomor rekening yang tersedia.

## Riwayat dan keamanan
- Semua unggahan, hasil baca AI, kecocokan surat, perubahan pencairan, dan bukti transfer akan
  memiliki riwayat agar dapat ditelusuri.
- Dokumen dan bukti transfer hanya dapat dibuka oleh peran yang berwenang.

## Asumsi yang digunakan
- Akun Admin/PIC yang sudah ada otomatis diperlakukan sebagai **Admin Provinsi** tanpa perubahan
  cakupan akses.
- Admin Wilayah hanya melihat Data PM milik wilayahnya sendiri.
- Nomor rekening mahasiswa dicatat pada Data PM agar hasil pembacaan bukti transfer dapat ditandai
  sesuai, tidak sesuai, atau perlu ditinjau. Nomor rekening ditampilkan secara tersamarkan.
- Bukti transfer massal dapat dihubungkan ke beberapa mahasiswa. Jika bukti hanya menunjukkan
  rekening kampus atau tidak memiliki petunjuk yang cukup untuk memetakan mahasiswa, hasilnya
  akan menunggu pemetaan atau konfirmasi Admin Provinsi/Super Admin.
- Status awal tiap tahap adalah **Belum Diproses**; Admin Provinsi atau Super Admin dapat memilih
  status berikutnya sesuai proses operasional pencairan.

# Proposal — Sinkronisasi Nama Calon Penerima Manfaat

## Tujuan
Menyamakan nama yang tampil pada area **Calon Penerima Manfaat** dengan isian
**Nama Lengkap** mahasiswa pada Data Pribadi.

## Perilaku yang akan diterapkan

1. Mahasiswa mengisi atau memperbarui kolom **Nama Lengkap** pada Data Pribadi,
   lalu menekan tombol **Simpan**.
2. Setelah penyimpanan berhasil, nama pada header akun mahasiswa langsung
   berubah mengikuti Nama Lengkap terbaru tanpa perlu keluar atau masuk kembali.
3. Nama yang sama akan digunakan kembali saat mahasiswa membuka akun pada sesi
   berikutnya, sehingga tampilan akun tetap konsisten.
4. Jika Nama Lengkap dikosongkan atau penyimpanan gagal, nama yang sudah tampil
   sebelumnya tidak akan ditimpa dengan nilai kosong.
5. ID Calon Penerima Manfaat tetap tidak berubah; perubahan hanya berlaku pada
   nama tampilan.

## Asumsi

- Nama yang ditampilkan mengikuti penulisan yang dimasukkan mahasiswa pada
  kolom **Nama Lengkap**, termasuk kapitalisasi yang dipilih mahasiswa.
- Sinkronisasi hanya dijalankan setelah tombol **Simpan** berhasil, bukan saat
  mahasiswa masih mengetik.

# Proposal — Google OAuth Redirect URI

## Kondisi saat ini

- Google OAuth aplikasi memakai layanan OAuth terkelola.
- Pengguna kembali ke dashboard pada domain yang sedang mereka buka.
- Untuk preview saat ini, alamat kembali aplikasi adalah:
  `https://sistem-registrasi.preview.emergentagent.com/dashboard`
- Pada domain sendiri, alamat kembali menjadi:
  `https://<domain-anda>/dashboard`.

## Keputusan bila OAuth Google milik organisasi digunakan

- Tetap memakai OAuth terkelola yang ada, atau menggantinya dengan kredensial Google milik organisasi.
- Bila diganti, callback Google Console perlu ditentukan dan diuji ulang bersama alur masuk Google.

## Asumsi

- Tidak ada perubahan autentikasi yang diminta; informasi ini hanya menjelaskan alamat kembali aplikasi saat ini.

# Proposal — Kredensial OAuth Google Milik Organisasi

## Tujuan

- Menambahkan konfigurasi rahasia `GOOGLE_CLIENT_ID` dan `GOOGLE_CLIENT_SECRET`.
- Menggunakan kredensial tersebut untuk alur masuk Google yang dikelola aplikasi, tanpa mengganggu akun email/password yang sudah ada.

## Yang perlu disiapkan

- Nilai Client ID dan Client Secret dari Google Cloud Console.
- JavaScript Origin untuk domain preview, domain produksi, dan setiap domain sendiri yang digunakan.
- Redirect URI untuk masing-masing domain dengan pola `/auth/google`.

## Perilaku yang diusulkan

- Redirect selalu mengikuti domain yang sedang dibuka pengguna, sehingga preview dan domain sendiri tidak tertukar.
- Bila kredensial belum tersedia atau belum valid, alur Google tidak menggantikan login email/password yang sudah ada.
- Login Google tetap memakai perlindungan state dan sesi aman.

## Asumsi yang dapat ditinjau

- Belum ada domain sendiri yang perlu didaftarkan. Jika ada, domain tersebut perlu ditambahkan sebagai JavaScript Origin dan Redirect URI di Google Cloud Console.
- Nilai rahasia akan diberikan melalui konfigurasi rahasia, bukan ditampilkan pada halaman aplikasi atau disimpan di kode.