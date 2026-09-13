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