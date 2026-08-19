# LEADS Lite Scraper

Standalone subsystem: pick a platform (Zameen or OLX), a city, and a lead
count. It scrapes only `seller_name` + `contact` + `platform`, shows a live
progress bar over WebSocket, stops itself once the count is hit, and lets
you export the result as CSV.

Reuses the same Scrapy settings/middlewares/pipeline pattern as the main
LEADS scraper — just a lighter item and a pipeline that stops the spider
early and reports progress back to FastAPI.

## Stack
- **Scraper**: Scrapy + Playwright (same spiders logic as LEADS, stripped to leads-only)
- **Backend**: FastAPI, runs Scrapy as a subprocess per job, WebSocket for live progress
- **DB**: MongoDB in Docker (separate port `27018` so it can run next to your main LEADS Mongo on `27017`)
- **Frontend**: React (Vite), plain CSS — white bg, black buttons/text

## 1. Start MongoDB
```bash
docker compose up -d
```

## 2. Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium

cp .env.example .env
# fill in OLX_ACCESS_TOKEN / OLX_ID_TOKEN in .env (same values you already
# use in the main LEADS project — they expire periodically, refresh if OLX
# leads start coming back with empty contact)

uvicorn app.main:app --reload --port 8000
```

## 3. Frontend
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173

## How it works
1. Frontend posts `{platform, city, count}` to `POST /api/scrape/start`.
2. Backend spawns `scrapy crawl <platform>_lite -a city=... -a limit=... -a job_id=...` as a subprocess.
3. Frontend opens `ws://.../api/ws/jobs/{job_id}`.
4. Every scraped lead → pipeline saves to Mongo → POSTs progress to `/internal/jobs/{job_id}/progress` → backend broadcasts over the websocket.
5. Once `count` is hit, the pipeline raises `CloseSpider("target_reached")`; the spider's `closed()` hook notifies `/internal/jobs/{job_id}/finished`.
6. Frontend shows "Export CSV" → hits `GET /api/scrape/{job_id}/export`, which streams a CSV built from Mongo.

## Notes
- `CONCURRENT_REQUESTS = 1` (same as your main scraper) means counts stop almost exactly at the requested number — no big overshoot.
- Cities are currently limited to the 5 that both spiders reliably support: Islamabad, Lahore, Karachi, Rawalpindi, Peshawar. Add more to `CITY_IDS` in `zameen_lite.py` and `CITIES`/`app/models.py` if you want more.
- If a job returns 0 leads, check `backend/scraper/job_<id>.log` — usually means the site changed a selector or you got rate-limited.
