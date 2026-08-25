import asyncio
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from web.etfline_sampler import run_etfline_sampler
from web.pages.etfline.router import router as etfline_router
from web.pages.getprice.router import router as getprice_router
from web.pages.home.router import router as home_router


BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(_: FastAPI):
    sampler = asyncio.create_task(run_etfline_sampler())
    try:
        yield
    finally:
        sampler.cancel()
        with suppress(asyncio.CancelledError):
            await sampler


app = FastAPI(title="JINX", version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.include_router(home_router)
app.include_router(getprice_router)
app.include_router(etfline_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
