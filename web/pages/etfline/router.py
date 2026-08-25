from pathlib import Path

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel
from fastapi.templating import Jinja2Templates

from store_skill.etfline import get_market_lines, get_sector_lines, list_sectors

router = APIRouter(prefix="/etfline")


class LinesRequest(BaseModel):
    codes: list[str]
    date: str | None = None
    source: str = "auto"


templates = Jinja2Templates(directory=Path(__file__).parent)


@router.get("")
def page(request: Request):
    return templates.TemplateResponse(request, "index.html")


@router.get("/api/sectors")
def sectors(sector_type: str = "industry", source: str = "auto"):
    return list_sectors(sector_type, source).to_dict()


@router.get("/api/lines")
def lines(codes: list[str] = Query(...), date: str | None = None, source: str = "auto"):
    return get_sector_lines(codes, date, source).to_dict()


@router.post("/api/lines")
def lines_post(payload: LinesRequest):
    return get_sector_lines(payload.codes, payload.date, payload.source).to_dict()


@router.get("/api/market")
def market(date: str | None = None):
    return get_market_lines(date).to_dict()
