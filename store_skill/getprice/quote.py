from __future__ import annotations

from typing import Iterable

from store_skill.getprice.config import DEFAULT_CONFIG, QuoteConfig, load_config_from_env
from store_skill.getprice.normalize import SymbolInfo, normalize_symbol
from store_skill.getprice.sources import SOURCE_REGISTRY
from store_skill.getprice.types import SkillResult


def _resolve_config(config: QuoteConfig | None) -> QuoteConfig:
    return load_config_from_env() if config is None else config


def _identity(info: SymbolInfo) -> tuple[str, str]:
    return info.market, info.symbol


def _row_identity(row: dict) -> tuple[str, str]:
    return str(row.get("market") or ""), str(row.get("symbol") or "")


def _identity_key(identity: tuple[str, str]) -> str:
    return f"{identity[0]}:{identity[1]}"


def _source_supports(info: SymbolInfo, name: str) -> bool:
    if name in {"eastmoney", "sina", "xueqiu", "tushare"}:
        return info.market in {"SH", "SZ", "BJ"}
    if name in {"yahoo", "yahoo_alt"}:
        return info.market in {"HK", "US"}
    return True


def _try_sources_one(info: SymbolInfo, config: QuoteConfig) -> SkillResult:
    errors: list[str] = []
    chain = [name for name in config.source_chain() if _source_supports(info, name)]
    if not chain:
        return SkillResult(ok=False, error=f"no compatible quote source for {info.market}", meta={"tried": config.source_chain()})
    for name in chain:
        source = SOURCE_REGISTRY.get(name)
        if source is None:
            errors.append(f"{name}: unknown source")
            continue
        try:
            data = source.fetch_one(info, timeout=config.timeout_sec, source_config=config.sources[name])
            return SkillResult(ok=True, data=data, meta={"tried": chain, "used": name, "source": name, "time": data.get("time")})
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{name}: {exc}")
    return SkillResult(ok=False, error=" | ".join(errors), meta={"tried": chain})


def get_quote(symbol: str, config: QuoteConfig | None = None) -> SkillResult:
    """Fetch one A-share, Hong Kong, or US quote with automatic fallback."""
    cfg = _resolve_config(config)
    try:
        info = normalize_symbol(symbol)
    except ValueError as exc:
        return SkillResult(ok=False, error=str(exc))
    return _try_sources_one(info, cfg)


def _metadata(rows: list[dict], chain: list[str], *, mode: str, partial: bool) -> dict:
    return {
        "tried": chain,
        "mode": mode,
        "count": len(rows),
        "partial": partial,
        "sources": sorted({str(row.get("source")) for row in rows if row.get("source")}),
        "times": {
            _identity_key(_row_identity(row)): row.get("time")
            for row in rows
        },
    }


def get_quotes(symbols: Iterable[str], config: QuoteConfig | None = None) -> SkillResult:
    """Fetch mixed-market quotes in input order with partial success support."""
    cfg = _resolve_config(config)
    requested: list[tuple[str, SymbolInfo]] = []
    errors: list[str] = []
    for raw in symbols:
        try:
            requested.append((raw, normalize_symbol(raw)))
        except ValueError as exc:
            errors.append(f"{raw}: {exc}")
    if not requested:
        return SkillResult(ok=False, error="no valid symbols; " + "; ".join(errors))

    chain = cfg.source_chain()
    rows_by_identity: dict[tuple[str, str], dict] = {}
    a_infos = [info for _, info in requested if info.sina_code]
    if "sina" in chain and a_infos:
        try:
            rows = SOURCE_REGISTRY["sina"].fetch_many(a_infos, timeout=cfg.timeout_sec, source_config=cfg.sources["sina"])
            rows_by_identity.update({_row_identity(row): row for row in rows})
        except Exception as exc:  # noqa: BLE001
            errors.append(f"sina-batch: {exc}")

    for raw, info in requested:
        identity = _identity(info)
        if identity in rows_by_identity:
            continue
        one = _try_sources_one(info, cfg)
        if one.ok:
            rows_by_identity[identity] = one.data
        else:
            errors.append(f"{raw}: {one.error}")

    ordered_rows = [rows_by_identity[_identity(info)] for _, info in requested if _identity(info) in rows_by_identity]
    if not ordered_rows:
        return SkillResult(ok=False, error=" | ".join(errors), meta={"tried": chain, "partial": bool(errors)})
    return SkillResult(ok=True, data=ordered_rows, error="; ".join(errors) if errors else None, meta=_metadata(ordered_rows, chain, mode="mixed-order", partial=bool(errors)))


__all__ = ["get_quote", "get_quotes", "DEFAULT_CONFIG"]
