from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import scrape, export, internal

app = FastAPI(title="LEADS Lite Scraper")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scrape.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(internal.router, prefix="/internal")


@app.get("/")
def root():
    return {"status": "ok", "service": "leads-lite-scraper"}
