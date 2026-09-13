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
- Admin Pendaftaran: admin.mdj@baznasbazisdki.id / AdminMDJ2026! / admin
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

## Super admin only
- GET/POST /api/admin/users
  (create regional admin: {name,email,password,role:"admin_wilayah",region:"Jakarta Barat"})
- PUT /api/admin/users/{user_id} {is_active}
- PUT /api/site/content {content:{...}}
- POST /api/site/banner (multipart file)
