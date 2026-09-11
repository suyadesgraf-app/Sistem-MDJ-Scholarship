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

## Admin flow (admin/super_admin)
- GET /api/admin/participants
- GET /api/admin/participants/{user_id}
- PUT /api/admin/participants/{user_id}/status {status, note}
- GET /api/admin/stats

## Super admin only
- GET/POST /api/admin/users  (create admin: {name,email,password,role:"admin"})
- PUT /api/admin/users/{user_id} {is_active}
- PUT /api/site/content {content:{...}}
- POST /api/site/banner (multipart file)
