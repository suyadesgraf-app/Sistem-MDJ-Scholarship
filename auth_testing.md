# MDJ Scholarship — Auth Testing Playbook

Two auth methods coexist:
1. Email/Password JWT — login returns `{user, token}` and sets httpOnly `access_token` cookie.
2. Google (Emergent-managed) — sets `session_token` cookie.

Both are accepted via cookie OR `Authorization: Bearer <token>` header.

## Super admin
- Email: supri@baznasbazisdki.id
- Password: MdjSuper2026!
- Role: super_admin

## Automatic demo identities
- Mahasiswa: mahasiswa.mdj@baznasbazisdki.id / MahasiswaMDJ2026! / student
- Admin Provinsi: admin.mdj@baznasbazisdki.id / AdminMDJ2026! / admin
- Super Admin: supri@baznasbazisdki.id / MdjSuper2026! / super_admin
- Tombol akun demo pada `/login` menjalankan `POST /api/auth/login` yang sama dengan formulir
  standar, lalu mengarahkan pengguna berdasarkan peran. Tidak ada endpoint bypass autentikasi.

## API test (curl)
```
API=$REACT_APP_BACKEND_URL
# login
curl -s -X POST "$API/api/auth/login" -H "Content-Type: application/json" \
  -d '{"email":"supri@baznasbazisdki.id","password":"MdjSuper2026!"}'
# use returned token
curl -s "$API/api/auth/me" -H "Authorization: Bearer <TOKEN>"
```

## Student flow
- POST /api/auth/register -> becomes student
- PUT /api/profile {data:{...}}
- POST /api/registration {category, action:"submit"}
- POST /api/documents (multipart: doc_type, file)

## Admin flow (admin/super_admin/admin_wilayah)
- GET /api/admin/participants
- GET /api/admin/participants/{user_id}
- PUT /api/admin/participants/{user_id}/status {status, note}
- GET /api/admin/stats

## Admin Wilayah
- Role: `admin_wilayah` dengan field `region` yang harus berupa salah satu dari enam wilayah DKI.
- Admin/PIC Provinsi dan Super Admin dapat membuat akun ini melalui `POST /api/admin/users`.
- Admin/PIC hanya boleh membuat serta mengelola `admin_wilayah`; Super Admin boleh mengelola semua role.
- Peserta, statistik, detail, perubahan status, ekspor Excel, verifikasi AI, dan impor seleksi wajib
  tersaring di server menurut `region` akun, termasuk bila query meminta `all` atau wilayah lain.
- Uji penolakan: Admin Wilayah membuka atau mengubah peserta di luar wilayah harus menerima HTTP 404.

## Penerima Manfaat dan Pencairan
- Role `admin` ditampilkan sebagai **Admin Provinsi**. Hanya `super_admin` boleh membuat role ini.
- `admin` dan `super_admin` dapat mengelola Data PM, rekening terenkripsi, surat mahasiswa aktif,
  bukti transfer, pencairan Tahap I/II, serta daftar tinjauan.
- `admin_wilayah` hanya dapat membaca Data PM di `region` miliknya. Permintaan region lain harus tetap
  tersaring di server; perubahan rekening, unggah berkas, pencairan, tinjauan, dan unduh sumber harus 403.
- Surat aktif dan bukti transfer hanya cocok otomatis bila nama dan NIM sama persis terhadap peserta
  berstatus `lolos`; data kosong, ganda, atau tidak cocok masuk `beneficiary_reviews`.
- Nomor rekening hanya tersimpan dalam bentuk terenkripsi dan respons API hanya boleh mengembalikan
  nomor tersamarkan. Status pencairan tidak boleh berubah otomatis oleh hasil OCR.
- `GET /api/admin/disbursements/campuses` mengembalikan agregat kampus dari peserta status `lolos`.
  Detail dan perubahan menggunakan kombinasi campus_key + region + stage; Admin Wilayah hanya baca
  data untuk region miliknya.
- `POST /api/admin/disbursements/transfer-proofs` menerima bukti transfer untuk Tahap I/II. Bukti
  sumber ditautkan ke banyak agregat, tidak disalin untuk setiap kampus atau wilayah.
- Tahap aktif selalu eksplisit: `GET /api/admin/beneficiary-reviews?stage=1|2` dan
  `GET /api/admin/disbursements/campuses/{campus_key}/audit?stage=1|2` hanya mengembalikan tahap
  yang diminta. Nilai stage selain `1` atau `2` harus ditolak dengan HTTP 400.
- `POST /api/admin/disbursements/transfer-proofs` wajib menerima `region` yang persis sama dengan
  salah satu wilayah DKI. Tidak ada OCR sebelum region lolos validasi. Region unggahan juga menjadi
  batas pencocokan otomatis dan pemetaan manual antrean tinjauan.
- Pencocokan bukti transfer tidak menggunakan nama/NIM mahasiswa. Ia mewajibkan nama kampus, nomor
  rekening kampus, dan atas nama rekening yang sama dengan master kampus terenkripsi.
- Endpoint mahasiswa `GET /api/student/disbursement-proofs` dan
  `GET /api/student/disbursement-proofs/{source_id}` hanya menampilkan/membuka bukti yang tertaut
  pada `recipient_user_ids` pengguna yang sedang masuk.
- Persetujuan massal Surat Aktif AI selalu mengirim `workflow` dan `source_ids`; backend menolak
  persetujuan semua tanpa cakupan sumber dan menandai rekomendasi stale bila status peserta berubah.

## Super admin only
- GET/POST /api/admin/users
  (create regional admin: {name,email,password,role:"admin_wilayah",region:"Jakarta Barat"})
- PUT /api/admin/users/{user_id} {is_active}
- PUT /api/site/content {content:{...}}
- POST /api/site/banner (multipart file)
