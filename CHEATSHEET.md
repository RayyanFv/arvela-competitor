# Arvela Cheatsheet - Dari Ticket Sampai Push GitHub

## 1) Start Semua Service

### API
```powershell
C:/Users/ACER/AppData/Local/Python/pythoncore-3.14-64/python.exe main.py --mode api --host 127.0.0.1 --port 8013
```

### Dashboard
```powershell
C:/Users/ACER/AppData/Local/Python/pythoncore-3.14-64/python.exe -m streamlit run ui/dashboard.py --server.address 127.0.0.1 --server.port 8502
```

Buka dashboard di:
- http://127.0.0.1:8502

## 2) Alur Paling Gampang (Disarankan)

1. Buka tab **Manual Ticket**.
2. Di bagian **Tech Workflow Focus**:
   - Isi Feature / Epic
   - Isi Working Branch
   - Pilih Target Environment
3. Klik **Autofill Dev -> QA -> Deployment Command**.
4. Pastikan **Assign to Agent = cto**.
5. Klik **Submit Manual Ticket**.
6. Simpan:
   - `ticket_id`
   - `run_id`
7. Buka tab **Audit Log** untuk lihat detail ticket JSON.
8. Buka tab **Runs** untuk cek artifact output run.

## 3) Mengubah Plan Jadi Development Nyata

Output CTO itu planning, bukan auto coding. Lanjutkan seperti ini:

1. Buat branch kerja:
```powershell
git checkout -b feature/tech-hardening
```
2. Ambil 1 task dari output CTO, implement di kode.
3. Jalankan test lokal.
4. Commit kecil per task:
```powershell
git add .
git commit -m "feat: implement canary analysis step"
```
5. Ulangi sampai checklist QA dan deploy gate terpenuhi.

## 4) Push ke GitHub

Cek remote:
```powershell
git remote -v
```

Kalau belum ada:
```powershell
git remote add origin https://github.com/RayyanFv/arvela-competitor.git
```

Push branch:
```powershell
git push -u origin feature/tech-hardening
```

Kalau mau langsung ke main:
```powershell
git push -u origin main
```

## 5) Definition of Done Sebelum Push

- Ticket CTO status complete
- Unit/integration test minimal pass
- Tidak ada secret di commit
- Commit message jelas
- PR/branch punya ringkasan perubahan

## 6) Kalau Submit Manual Ticket Gagal

1. Refresh browser (Ctrl+F5).
2. Pastikan Task Command tidak kosong.
3. Restart Streamlit:
```powershell
C:/Users/ACER/AppData/Local/Python/pythoncore-3.14-64/python.exe -m streamlit run ui/dashboard.py --server.address 127.0.0.1 --server.port 8502
```
4. Coba submit lagi di tab Manual Ticket.
