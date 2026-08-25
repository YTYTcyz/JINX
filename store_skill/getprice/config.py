from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from typing import Any


DEFAULT_REFERER = "https://finance.sina.com.cn/"


@dataclass
class SourceConfig:
    enabled: bool = True
    referer: str = DEFAULT_REFERER
    cookie: str = ""
    token: str = ""


@dataclass
class QuoteConfig:
    primary: str = "eastmoney"
    fallback: list[str] = field(default_factory=lambda: ["sina", "yahoo", "yahoo_alt", "xueqiu"])
    timeout_sec: float = 10.0
    sources: dict[str, SourceConfig] = field(default_factory=dict)

    def __post_init__(self) -> None:
        defaults = {
            "eastmoney": SourceConfig(enabled=True),
            "sina": SourceConfig(enabled=True, referer=DEFAULT_REFERER),
            "xueqiu": SourceConfig(enabled=True),
            "tushare": SourceConfig(enabled=False),
            "yahoo": SourceConfig(enabled=True),
            "yahoo_alt": SourceConfig(enabled=True),
        }
        merged: dict[str, SourceConfig] = {}
        for name, default in defaults.items():
            user = self.sources.get(name)
            if user is None:
                merged[name] = default
            elif isinstance(user, SourceConfig):
                merged[name] = user
            elif isinstance(user, dict):
                merged[name] = SourceConfig(
                    enabled=bool(user.get("enabled", default.enabled)),
                    referer=str(user.get("referer", default.referer)),
                    cookie=str(user.get("cookie", default.cookie)),
                    token=str(user.get("token", default.token)),
                )
            else:
                merged[name] = default
        for name, user in self.sources.items():
            if name not in merged:
                if isinstance(user, SourceConfig):
                    merged[name] = user
                elif isinstance(user, dict):
                    merged[name] = SourceConfig(**user)
        self.sources = merged

    def source_chain(self) -> list[str]:
        ordered: list[str] = []
        for name in [self.primary, *self.fallback]:
            if name and name not in ordered:
                ordered.append(name)
        result: list[str] = []
        for name in ordered:
            cfg = self.sources.get(name)
            if cfg is None or not cfg.enabled:
                continue
            if name == "tushare" and not (cfg.token or "").strip():
                continue
            result.append(name)
        return result

    def copy(self, **kwargs: Any) -> QuoteConfig:
        return replace(self, **kwargs)


def _parse_fallback(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


def load_config_from_env(base: QuoteConfig | None = None) -> QuoteConfig:
    cfg = base or QuoteConfig()
    primary = os.getenv("JINX_QUOTE_PRIMARY", cfg.primary).strip() or cfg.primary
    fallback_env = os.getenv("JINX_QUOTE_FALLBACK")
    fallback = _parse_fallback(fallback_env) if fallback_env is not None else list(cfg.fallback)
    timeout_raw = os.getenv("JINX_QUOTE_TIMEOUT")
    timeout_sec = float(timeout_raw) if timeout_raw else cfg.timeout_sec

    sources = {k: SourceConfig(**vars(v)) for k, v in cfg.sources.items()}

    xq_cookie = os.getenv("JINX_XUEQIU_COOKIE")
    if xq_cookie is not None:
        sources["xueqiu"] = SourceConfig(
            enabled=sources["xueqiu"].enabled,
            cookie=xq_cookie,
        )

    ts_token = os.getenv("JINX_TUSHARE_TOKEN")
    if ts_token is not None:
        token = ts_token.strip()
        sources["tushare"] = SourceConfig(
            enabled=bool(token) or sources["tushare"].enabled,
            token=token,
        )
        if token:
            sources["tushare"].enabled = True

    sina_referer = os.getenv("JINX_SINA_REFERER")
    if sina_referer:
        sources["sina"] = SourceConfig(
            enabled=sources["sina"].enabled,
            referer=sina_referer,
        )

    return QuoteConfig(
        primary=primary,
        fallback=fallback,
        timeout_sec=timeout_sec,
        sources=sources,
    )


DEFAULT_CONFIG = load_config_from_env()
