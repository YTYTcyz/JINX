from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.templating import Jinja2Templates

from store_skill.getkline import get_kline
from store_skill.getprice import get_quote
from web.messages import friendly_error


router = APIRouter(prefix="/getprice")
templates = Jinja2Templates(directory=Path(__file__).parent)


@router.get("")
def page(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {"symbol": "600519", "result": None},
    )


@router.post("")
def query(request: Request, symbol: str = Form(...)):
    symbol = symbol.strip()
    result = get_quote(symbol)
    if not result.ok:
        result.error = friendly_error(result.error)
    return templates.TemplateResponse(
        request,
        "index.html",
        {"symbol": symbol, "result": result},
    )


@router.get("/kline/{symbol}")
def kline(symbol: str, period: str = "intraday"):
    result = get_kline(symbol, period)
    if not result.ok:
        result.error = friendly_error(result.error)
    return result.to_dict()
