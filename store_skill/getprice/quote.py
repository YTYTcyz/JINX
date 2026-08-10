from __future__ import annotations

from typing import Iterable

from store_skill.getprice.config import DEFAULT_CONFIG, QuoteConfig, load_config_from_env
from store_skill.getprice.normalize import SymbolInfo, normalize_symbol
from store_skill.getprice.sources import SOURCE_REGISTRY
from store_skill.getprice.types import SkillResult


def _resolve_config(config: QuoteConfig | None) -> QuoteConfig:
    if config is None:
        return load_config_from_env()
    return config


def _try_sources_one(info: SymbolInfo, config: QuoteConfig) -> SkillResult:
    errors: list[str] = []
    chain = config.source_chain()
    if not chain:
        return SkillResult(ok=False, error="no enabled quote sources in config")

    for name in chain:
        source = SOURCE_REGISTRY.get(name)
        if source is None:
            errors.append(f"{name}: unknown source")
            continue
        source_cfg = config.sources[name]
        try:
            data = source.fetch_one(
                info,
                timeout=config.timeout_sec,
                source_config=source_cfg,
            )
            return SkillResult(
                ok=True,
                data=data,
                meta={"tried": chain, "used": name},
            )
        except Exception as exc:  # noqa: BLE001 - aggregate source failures
            errors.append(f"{name}: {exc}")

    return SkillResult(
        ok=False,
        error=" | ".join(errors),
        meta={"tried": chain},
    )


def get_quote(symbol: str, config: QuoteConfig | None = None) -> SkillResult:
    """Fetch one A-share quote using CONFIG primary → fallback chain."""
    cfg = _resolve_config(config)
    try:
        info = normalize_symbol(symbol)
    except ValueError as exc:
        return SkillResult(ok=False, error=str(exc))
    return _try_sources_one(info, cfg)


def get_quotes(symbols: Iterable[str], config: QuoteConfig | None = None) -> SkillResult:
    """Fetch multiple A-share quotes.

    If `sina` is in the enabled chain, prefer one batch sina call first.
    Otherwise fetch symbol-by-symbol with the same fallback chain.
    """
    cfg = _resolve_config(config)
    infos: list[SymbolInfo] = []
    bad: list[str] = []
    for raw in symbols:
        try:
            infos.append(normalize_symbol(raw))
        except ValueError as exc:
            bad.append(f"{raw}: {exc}")

    if not infos:
        return SkillResult(ok=False, error="no valid symbols; " + "; ".join(bad))

    chain = cfg.source_chain()
    errors: list[str] = list(bad)

    if "sina" in chain:
        sina = SOURCE_REGISTRY["sina"]
        try:
            rows = sina.fetch_many(
                infos,
                timeout=cfg.timeout_sec,
                source_config=cfg.sources["sina"],
            )
            got = {r["symbol"] for r in rows}
            missing = [i for i in infos if i.symbol not in got]
            if not missing:
                return SkillResult(
                    ok=True,
                    data=rows,
                    meta={"tried": ["sina"], "used": "sina", "mode": "batch"},
                )
            # fill missing via normal chain
            filled = list(rows)
            for info in missing:
                one = _try_sources_one(info, cfg)
                if one.ok:
                    filled.append(one.data)
                else:
                    errors.append(f"{info.symbol}: {one.error}")
            if filled:
                return SkillResult(
                    ok=True,
                    data=filled,
                    meta={"tried": chain, "used": "sina+fallback", "mode": "batch+fill"},
                    error="; ".join(errors) if errors else None,
                )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"sina-batch: {exc}")

    results = []
    for info in infos:
        one = _try_sources_one(info, cfg)
        if one.ok:
            results.append(one.data)
        else:
            errors.append(f"{info.symbol}: {one.error}")

    if not results:
        return SkillResult(ok=False, error=" | ".join(errors), meta={"tried": chain})

    return SkillResult(
        ok=True,
        data=results,
        error="; ".join(errors) if errors else None,
        meta={"tried": chain, "mode": "per-symbol"},
    )


__all__ = ["get_quote", "get_quotes", "DEFAULT_CONFIG"]
