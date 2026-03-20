# Arvela Use Cases (Pergerakan Demo)

## Prasyarat
- API jalan (contoh di port 8013):
   - `C:/Users/ACER/AppData/Local/Python/pythoncore-3.14-64/python.exe main.py --mode api --host 127.0.0.1 --port 8013`
- Dashboard jalan (contoh di port 8502):
   - `C:/Users/ACER/AppData/Local/Python/pythoncore-3.14-64/python.exe -m streamlit run ui/dashboard.py --server.address 127.0.0.1 --server.port 8502`
- Pastikan semua endpoint API di bawah memakai host/port yang sama dengan saat API dijalankan.

## Nilai Yang Wajib Diganti
- `company_id`:
   - default: `arvela`
   - tenant baru: `arvela_clone` atau nama lain milikmu
- `webhook_url`:
   - jangan pakai placeholder `https://your-webhook-url`
   - pakai URL endpoint asli milikmu (contoh service test: webhook.site)
- `objective`:
   - isi dengan objective real sesuai fokus sprint/board saat itu

## Use Case 1 - Trigger Pipeline Manual (Board Action)
1. Buka dashboard tab `Run Pipeline`.
2. Isi objective: `Scale SQL 2x in 30 days with secure implementation roadmap`.
3. Klik `Run Now`.
4. Verifikasi output:
   - endpoint `GET /api/v1/arvela/runs`
   - endpoint `GET /api/v1/arvela/runs/{run_id}/report`

## Use Case 2 - Pause/Resume Agent (Governance)
1. Dashboard tab `Org Chart`, pilih agent `cmo`.
2. Klik `Pause Agent`.
3. Cek event override di audit:
   - `GET /api/v1/arvela/events`
4. Klik `Resume Agent` lalu cek event lagi.

## Use Case 3 - Heartbeat Otomatis Per-Agent
1. Jalankan heartbeat via API:
   - `POST /api/v1/arvela/heartbeat/start`
2. Cek status scheduler:
   - `GET /api/v1/arvela/heartbeat/status`
3. Verifikasi route per agent:
   - `ceo -> full_run`
   - `cpo -> product_sprint`
   - `cto -> product_sprint`
   - `cmo -> gtm_only`
4. Stop heartbeat:
   - `POST /api/v1/arvela/heartbeat/stop`

## Use Case 4 - Multi-Company Onboarding
1. Buat company baru:
   - `POST /api/v1/companies`
   - body contoh:
     {
       "company_id": "arvela_clone",
       "display_name": "Arvela Clone",
       "industry": "HR SaaS",
       "stage": "early_growth",
       "target_market": "Indonesia SMB",
       "mission": "Ship HR automation"
     }
2. Jalankan pipeline untuk company baru:
   - `POST /api/v1/arvela_clone/pipelines/full_run/run`
3. Cek output isolation:
   - `storage/arvela_clone/outputs/`

## Use Case 5 - Notification Routing Test
1. Simpan config notifikasi:
   - `POST /api/v1/arvela/notifications/config`
    - contoh body (ganti `webhook_url` dengan URL milikmu):
     {
       "enabled": true,
          "webhook_url": "https://webhook.site/<ganti-dengan-id-kamu>",
       "events": {
         "pipeline_complete": true,
         "dod_failure": true,
         "budget_limit_hit": true
       }
     }
2. Test kirim notifikasi:
   - `POST /api/v1/arvela/notifications/test`
3. Jalankan pipeline lalu verifikasi endpoint webhook menerima event `pipeline_complete`.

## Use Case 6 - Explore Cloned Competitor Repo
1. Buka dashboard tab `Config + Repo`.
2. Lihat `Cloned Repo Explorer`.
3. Verifikasi path clone:
   - `arvela-competitor/`
4. Gunakan sebagai input objective:
   - `Analyze competitor repo and propose 3 strategic differentiators.`
