from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date as date_type, datetime
from io import StringIO
from math import isfinite
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

import pandas as pd
import requests

from store_skill.etfline.types import SkillResult

_EM_LIST_URL = "https://push2.eastmoney.com/api/qt/clist/get"
_EM_LINE_URL = "https://push2his.eastmoney.com/api/qt/stock/fflow/kline/get"
_EM_MARKET_URL = "https://push2his.eastmoney.com/api/qt/stock/trends2/get"
_SINA_MARKET_URL = "https://quotes.sina.cn/cn/api/jsonp_v2.php/var%20_market=/CN_MarketDataService.getKLineData"
_MARKET_INDEXES = (("000001", "上证指数"), ("000680", "科创综指"), ("000688", "科创50"))
_THS_URLS = {
    "industry": "http://data.10jqka.com.cn/funds/hyzjl/field/tradezdf/order/desc/page/{page}/ajax/1/free/1/",
    "concept": "http://data.10jqka.com.cn/funds/gnzjl/field/tradezdf/order/desc/page/{page}/ajax/1/free/1/",
}
_SINA_INDUSTRY_URL = "http://vip.stock.finance.sina.com.cn/q/view/newSinaHy.php"
_SINA_OTHER_URL = "http://money.finance.sina.com.cn/q/view/newFLJK.php"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; JINX/0.1; sector data client)"}
_EM_FILTERS = {"industry": "m:90+t:2+f:!50", "concept": "m:90+t:3+f:!50"}
_SOURCES = {"auto", "eastmoney", "ths", "sina"}
_EM_LINE_WORKERS = 5


def _number(value: Any) -> float | None:
    try:
        text = str(value).strip().replace(",", "").replace("%", "")
        if text in {"", "-", "--", "None", "nan"}:
            return None
        number = float(text)
        return number if isfinite(number) else None
    except (TypeError, ValueError):
        return None


def _validate_sector_type(value: str) -> str:
    kind = str(value).strip().lower()
    if kind not in _EM_FILTERS:
        raise ValueError("板块类型仅支持 industry（行业）或 concept（概念）")
    return kind


def _validate_source(value: str) -> str:
    source = str(value or "auto").strip().lower()
    if source not in _SOURCES:
        raise ValueError("数据来源仅支持 auto、eastmoney、ths 或 sina")
    return source


def _validate_date(value: str | None) -> str:
    if value is None or not str(value).strip():
        return date_type.today().isoformat()
    try:
        parsed = datetime.strptime(str(value).strip(), "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("日期格式应为 YYYY-MM-DD，例如 2026-08-18") from exc
    if parsed > date_type.today():
        raise ValueError("不能查询未来日期，请选择今天或更早日期")
    return parsed.isoformat()


def _validate_codes(codes: Iterable[str] | str, source: str) -> list[str]:
    values = [codes] if isinstance(codes, str) else list(codes or [])
    normalized = []
    for raw in values:
        code = str(raw).strip().upper()
        valid = (
            (source in {"auto", "eastmoney"} and bool(re.fullmatch(r"BK\d{4}", code)))
            or (source in {"auto", "ths"} and code.startswith("THS-") and len(code) > 4)
            or (source in {"auto", "sina"} and code.startswith("SINA-") and len(code) > 5)
        )
        if not valid:
            raise ValueError(f"板块代码 {raw} 不属于所选数据源；切换来源后请先重新加载板块列表")
        if code not in normalized:
            normalized.append(code)
    if not normalized:
        raise ValueError("请至少选择一个板块")
    return normalized


def _meta(requested: str, actual: str | None, granularity: str, interval: int | None,
          fallbacks: list[str] | None = None, errors: list[str] | None = None, **extra: Any) -> dict[str, Any]:
    return {"requested_source": requested, "actual_source": actual, "fallbacks": fallbacks or [],
            "errors": errors or [], "granularity": granularity, "update_interval": interval, **extra}


def _request_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    response = requests.get(url, params=params, headers=_HEADERS, timeout=10)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or payload.get("rc") != 0:
        raise ValueError("东方财富返回异常")
    return payload


def _parse_sector_list(payload: dict[str, Any]) -> list[dict[str, Any]]:
    items = []
    for row in (payload.get("data") or {}).get("diff") or []:
        if not isinstance(row, dict):
            continue
        code, name = str(row.get("f12") or "").strip(), str(row.get("f14") or "").strip()
        if code.startswith("BK") and name:
            items.append({"code": code, "name": name, "price": _number(row.get("f2")),
                          "change_pct": _number(row.get("f3")), "main_net": _number(row.get("f62"))})
    return items


def _parse_line_payload(payload: dict[str, Any], wanted_date: str) -> dict[str, Any]:
    data, points = payload.get("data") or {}, []
    for raw in data.get("klines") or []:
        parts = str(raw).split(",")
        if len(parts) >= 2 and parts[0].strip()[:10] == wanted_date:
            value = _number(parts[1])
            if value is not None:
                points.append({"time": parts[0].strip(), "value": value})
    return {"code": str(data.get("code") or ""), "name": str(data.get("name") or data.get("code") or ""), "points": points}


def _eastmoney_list(kind: str) -> list[dict[str, Any]]:
    payload = _request_json(_EM_LIST_URL, {"pn": 1, "pz": 1000, "po": 1, "np": 1, "fltt": 2, "invt": 2,
        "fid": "f62", "fs": _EM_FILTERS[kind], "fields": "f2,f3,f12,f14,f62"})
    items = _parse_sector_list(payload)
    if not items:
        raise ValueError("东方财富未返回板块列表")
    return items


def _eastmoney_line(code: str, wanted_date: str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        payload = _request_json(_EM_LINE_URL, {"lmt": 300, "klt": 1, "secid": f"90.{code}",
            "fields1": "f1,f2,f3,f7", "fields2": "f51,f52,f53,f54,f55,f56"})
        line = _parse_line_payload(payload, wanted_date)
        if line["points"]:
            line["code"] = code
            return line, None
        return None, f"{code} 在 {wanted_date} 无分钟数据"
    except (requests.RequestException, ValueError, TypeError) as exc:
        return None, f"{code}：{exc}"


def _eastmoney_lines(codes: list[str], wanted_date: str) -> tuple[list[dict[str, Any]], list[str]]:
    # executor.map preserves input order while limiting pressure on the public API.
    with ThreadPoolExecutor(max_workers=min(_EM_LINE_WORKERS, len(codes))) as executor:
        results = list(executor.map(lambda code: _eastmoney_line(code, wanted_date), codes))
    return ([line for line, _ in results if line is not None],
            [failure for _, failure in results if failure is not None])


def _parse_market_payload(payload: dict[str, Any], code: str, name: str, wanted_date: str) -> dict[str, Any]:
    points = []
    for raw in (payload.get("data") or {}).get("trends") or []:
        parts = str(raw).split(",")
        if len(parts) >= 3 and parts[0].strip()[:10] == wanted_date:
            value = _number(parts[2])
            if value is not None:
                points.append({"time": parts[0].strip(), "value": value})
    return {"code": code, "name": name, "points": points}


def _eastmoney_market_line(code: str, name: str, wanted_date: str) -> dict[str, Any]:
    payload = _request_json(_EM_MARKET_URL, {"ndays": 5, "iscr": 0, "iscca": 0,
        "secid": f"1.{code}", "fields1": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58"})
    line = _parse_market_payload(payload, code, name, wanted_date)
    if not line["points"]:
        raise ValueError(f"{code} 在 {wanted_date} 无指数分钟数据")
    return line


def _parse_sina_market_payload(text: str, code: str, name: str, wanted_date: str) -> dict[str, Any]:
    start, end = text.find("["), text.rfind("]")
    if start < 0 or end < start:
        raise ValueError("新浪返回内容不是指数分钟 JSON")
    rows = json.loads(text[start:end + 1])
    points = []
    for row in rows if isinstance(rows, list) else []:
        stamp = str(row.get("day") or row.get("date") or "").strip()
        value = _number(row.get("close"))
        if stamp[:10] == wanted_date and value is not None:
            points.append({"time": stamp, "value": value})
    return {"code": code, "name": name, "points": points}


def _sina_market_line(code: str, name: str, wanted_date: str) -> dict[str, Any]:
    response = requests.get(_SINA_MARKET_URL, params={"symbol": f"sh{code}", "scale": 1,
        "ma": "no", "datalen": 1023}, headers=_HEADERS, timeout=10)
    response.raise_for_status()
    line = _parse_sina_market_payload(response.text, code, name, wanted_date)
    if not line["points"]:
        raise ValueError(f"{code} 在 {wanted_date} 无指数分钟数据")
    return line


def _namespace_code(prefix: str, kind: str, name: str) -> str:
    digest = hashlib.sha1(f"{kind}:{name}".encode("utf-8")).hexdigest()[:12].upper()
    return f"{prefix}-{digest}"


def _find_column(columns: Iterable[Any], *needles: str) -> Any | None:
    for column in columns:
        compact = re.sub(r"\s+", "", str(column))
        if all(needle in compact for needle in needles):
            return column
    return None


def _parse_ths_html(html: str, kind: str) -> list[dict[str, Any]]:
    try:
        tables = pd.read_html(StringIO(html))
    except (ValueError, ImportError) as exc:
        raise ValueError(f"同花顺表格解析失败：{exc}") from exc
    for frame in tables:
        name_col = _find_column(frame.columns, "行业" if kind == "industry" else "概念")
        if name_col is None:
            name_col = _find_column(frame.columns, "板块")
        net_col = _find_column(frame.columns, "净额")
        if name_col is None or net_col is None:
            continue
        price_col = _find_column(frame.columns, "指数")
        change_col = _find_column(frame.columns, "涨跌幅")
        items = []
        for _, row in frame.iterrows():
            name = str(row.get(name_col, "")).strip()
            net_yi = _number(row.get(net_col))
            if not name or name.lower() == "nan" or net_yi is None:
                continue
            items.append({"code": _namespace_code("THS", kind, name), "name": name,
                "price": _number(row.get(price_col)) if price_col is not None else None,
                "change_pct": _number(row.get(change_col)) if change_col is not None else None,
                "main_net": round(net_yi * 100_000_000, 2)})
        if items:
            return items
    raise ValueError("同花顺页面未找到包含板块和净额的表格，请稍后重试或检查上游字段")


def _ths_list(kind: str) -> list[dict[str, Any]]:
    items, seen = [], set()
    for page in range(1, 21):
        try:
            response = requests.get(_THS_URLS[kind].format(page=page), headers=_HEADERS, timeout=10)
            response.raise_for_status()
            page_items = _parse_ths_html(response.text, kind)
        except (requests.RequestException, ValueError) as exc:
            if items:
                break
            raise exc
        added = 0
        for item in page_items:
            if item["code"] not in seen:
                seen.add(item["code"]); items.append(item); added += 1
        if added == 0 or len(page_items) < 20:
            break
    if not items:
        raise ValueError("同花顺未返回板块资金快照")
    return items


def _cache_dir() -> Path:
    configured = os.getenv("JINX_ETFLINE_CACHE_DIR")
    return Path(configured).expanduser() if configured else Path.home() / ".cache" / "jinx" / "etfline"


def _cache_file(day: str) -> Path:
    return _cache_dir() / f"ths-{day}.json"


def _write_ths_snapshot(items: list[dict[str, Any]], kind: str, now: datetime | None = None) -> str | None:
    current = now or datetime.now(ZoneInfo("Asia/Shanghai"))
    bucket = current.replace(minute=(current.minute // 5) * 5, second=0, microsecond=0)
    clock = bucket.strftime("%H:%M")
    if clock > "15:00":
        bucket = bucket.replace(hour=15, minute=0)
    elif "11:30" < clock < "13:00":
        bucket = bucket.replace(hour=11, minute=30)
    stamp, path = bucket.strftime("%Y-%m-%d %H:%M"), _cache_file(bucket.date().isoformat())
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "source": "ths", "samples": {}}
        if path.exists():
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict) and isinstance(loaded.get("samples"), dict):
                payload = loaded
        for item in items:
            value = item.get("main_net")
            if value is not None:
                entry = payload["samples"].setdefault(item["code"], {"name": item["name"], "sector_type": kind, "points": {}})
                entry.update({"name": item["name"], "sector_type": kind})
                entry["points"][stamp] = value
        fd, temporary = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, separators=(",", ":")); handle.flush(); os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary): os.unlink(temporary)
        return None
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return f"同花顺快照缓存写入失败：{exc}；本次实时查询仍可使用"


def _read_ths_lines(codes: list[str], wanted_date: str) -> tuple[list[dict[str, Any]], list[str]]:
    path = _cache_file(wanted_date)
    if not path.exists():
        raise ValueError(f"{wanted_date} 尚无本服务实际采集的同花顺快照；请保持服务运行并等待交易时段采样")
    try:
        samples = json.loads(path.read_text(encoding="utf-8")).get("samples", {})
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"同花顺快照缓存无法读取：{exc}；请保持服务运行并等待交易时段重新采样") from exc
    lines, failures = [], []
    for code in codes:
        entry = samples.get(code)
        points = [] if not entry else [
            {"time": stamp, "value": value}
            for stamp, value in sorted(entry.get("points", {}).items())
            if stamp[:10] == wanted_date
            and ("09:30" <= stamp[11:16] <= "11:30" or "13:00" <= stamp[11:16] <= "15:00")
            and _number(value) is not None
        ]
        if points:
            lines.append({"code": code, "name": str(entry.get("name") or code), "points": points})
        else:
            failures.append(f"{code} 在 {wanted_date} 无本服务采样点")
    return lines, failures


def _parse_sina_payload(text: str, kind: str) -> list[dict[str, Any]]:
    start = text.find("{")
    if start < 0:
        raise ValueError("新浪返回内容不是板块 JSON")
    payload, _ = json.JSONDecoder().raw_decode(text[start:])
    items = []
    for key, raw in payload.items():
        values = raw.split(",") if isinstance(raw, str) else []
        if len(values) < 6:
            continue
        name = values[1].strip()
        if not name:
            continue
        label = values[0].strip() or str(key)
        code = "SINA-" + re.sub(r"[^A-Za-z0-9_-]", "", label).upper()
        if code == "SINA-": code = _namespace_code("SINA", kind, name)
        items.append({"code": code, "name": name, "price": _number(values[3]),
                      "change_pct": _number(values[5]), "main_net": None})
    if not items:
        raise ValueError("新浪未返回可识别的板块行情")
    return items


def _sina_list(kind: str) -> list[dict[str, Any]]:
    if kind == "industry":
        response = requests.get(_SINA_INDUSTRY_URL, headers=_HEADERS, timeout=10)
    else:
        response = requests.get(_SINA_OTHER_URL, params={"param": "class"}, headers=_HEADERS, timeout=10)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or "gbk"
    return _parse_sina_payload(response.text, kind)


def list_sectors(sector_type: str = "industry", source: str = "auto") -> SkillResult:
    """Return real sector snapshots from Eastmoney, THS, or Sina."""
    try:
        kind, requested = _validate_sector_type(sector_type), _validate_source(source)
    except (ValueError, TypeError) as exc:
        return SkillResult(ok=False, error=str(exc), meta=_meta(str(source), None, "snapshot", None))
    chain = [requested] if requested != "auto" else ["eastmoney", "ths", "sina"]
    errors, fallbacks = [], []
    for actual in chain:
        try:
            if actual == "eastmoney": items, interval = _eastmoney_list(kind), 60
            elif actual == "ths": items, interval = _ths_list(kind), 300
            else: items, interval = _sina_list(kind), 300
            warnings = []
            if actual == "ths":
                warning = _write_ths_snapshot(items, kind)
                if warning: warnings.append(warning)
            if actual == "sina": warnings.append("新浪仅提供真实板块行情快照，不含主力净流入，不能用于资金气泡或资金线")
            return SkillResult(ok=True, data={"sector_type": kind, "items": items, "source": actual},
                meta=_meta(requested, actual, "snapshot", interval, fallbacks, errors, count=len(items), warnings=warnings))
        except (requests.RequestException, ValueError, TypeError, json.JSONDecodeError) as exc:
            errors.append(f"{actual}：{exc}")
            if actual != chain[-1]: fallbacks.append(f"{actual} -> {chain[chain.index(actual)+1]}")
    return SkillResult(ok=False, error=f"获取板块列表失败：{'；'.join(errors)}。请检查网络或改选数据源后重试",
        meta=_meta(requested, None, "snapshot", None, fallbacks, errors))


def get_sector_lines(codes: Iterable[str] | str, date: str | None = None, source: str = "auto") -> SkillResult:
    """Return Eastmoney minute lines or this service's real THS five-minute samples."""
    try:
        requested, wanted_date = _validate_source(source), _validate_date(date)
        normalized = _validate_codes(codes, requested)
    except (ValueError, TypeError) as exc:
        return SkillResult(ok=False, error=str(exc), meta=_meta(str(source), None, "minute", None))
    families = {"ths" if code.startswith("THS-") else "sina" if code.startswith("SINA-") else "eastmoney" for code in normalized}
    if len(families) != 1:
        error = "一次请求不能混用不同来源的板块代码；请切换来源并重新加载列表"
        return SkillResult(ok=False, error=error, meta=_meta(requested, None, "snapshot", None, errors=[error]))
    actual = families.pop()
    if actual == "sina":
        error = "新浪板块接口仅有行情快照，不含真实主力净流入，因此不能生成资金线；请选择东方财富或等待服务端积累同花顺快照"
        return SkillResult(ok=False, error=error, meta=_meta(requested, "sina", "snapshot", 300, errors=[error]))
    try:
        if actual == "eastmoney":
            lines, failures = _eastmoney_lines(normalized, wanted_date); granularity, interval = "minute", 60
        else:
            lines, failures = _read_ths_lines(normalized, wanted_date); granularity, interval = "snapshot", 300
        if not lines:
            raise ValueError("；".join(failures) or "没有可用数据")
        return SkillResult(ok=True, data={"date": wanted_date, "lines": lines, "source": actual,
            "metric": "累计主力净流入" if actual == "eastmoney" else "主力净流入快照采样", "unit": "元"},
            meta=_meta(requested, actual, granularity, interval, errors=failures,
                       requested_count=len(normalized), returned=len(lines), warnings=failures))
    except (requests.RequestException, ValueError, TypeError, OSError) as exc:
        if actual == "eastmoney": suggestion = "请选择近期交易日或稍后重试"
        else: suggestion = "请保持服务运行并等待服务端在交易时段积累真实样本"
        error = f"获取{actual}资金线失败：{exc}。{suggestion}"
        return SkillResult(ok=False, error=error, meta=_meta(requested, actual,
            "minute" if actual == "eastmoney" else "snapshot", 60 if actual == "eastmoney" else 300, errors=[str(exc)]))


def get_market_lines(date: str | None = None) -> SkillResult:
    """Return real intraday closes for three fixed Shanghai market indexes."""
    try:
        wanted_date = _validate_date(date)
    except (ValueError, TypeError) as exc:
        return SkillResult(ok=False, error=str(exc), meta=_meta("eastmoney", None, "minute", None))
    lines, warnings, sources = [], [], []
    for code, name in _MARKET_INDEXES:
        try:
            line = _eastmoney_market_line(code, name, wanted_date); source = "eastmoney"
        except (requests.RequestException, ValueError, TypeError, json.JSONDecodeError) as east_error:
            warnings.append(f"{name}东方财富失败：{east_error}；已尝试新浪")
            try:
                line = _sina_market_line(code, name, wanted_date); source = "sina"
            except (requests.RequestException, ValueError, TypeError, json.JSONDecodeError) as sina_error:
                warnings.append(f"{name}新浪失败：{sina_error}")
                continue
        lines.append(line); sources.append(source)
    if len(lines) != len(_MARKET_INDEXES):
        missing = [name for code, name in _MARKET_INDEXES if not any(line["code"] == code for line in lines)]
        return SkillResult(ok=False, error=f"{wanted_date} 大盘分时数据不完整（缺少{'、'.join(missing)}），请确认交易日或稍后重试",
            meta=_meta("eastmoney", None, "minute", 60, errors=warnings, warnings=warnings))
    actual = sources[0] if len(set(sources)) == 1 else "mixed"
    return SkillResult(ok=True, data={"date": wanted_date, "lines": lines, "source": actual,
        "metric": "指数分时收盘点位", "unit": "点"}, meta=_meta("eastmoney", actual, "minute", 60,
        fallbacks=["eastmoney -> sina"] if "sina" in sources else [], errors=warnings, warnings=warnings, sources=sources))
