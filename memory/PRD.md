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

## Backlog / Remaining
- **P1**: Forgot/reset password flow; brute-force lockout on login.
- **P1**: Restrict GET /api/files to owner + admins (defense-in-depth).
- **P2**: Email notifications on status change (Resend).
- **P2**: Export participants to Excel/CSV.
- **P2**: Restrict CORS_ORIGINS to frontend origin.

## Test Credentials
See /app/memory/test_credentials.md. Demo mahasiswa, admin, dan super admin tersedia otomatis.
