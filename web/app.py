from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from web.pages.getprice.router import router as getprice_router
from web.pages.home.router import router as home_router


BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="JINX", version="0.1.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.include_router(home_router)
app.include_router(getprice_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
