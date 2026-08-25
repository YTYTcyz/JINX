from __future__ import annotations

import asyncio
import logging
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from store_skill.etfline import list_sectors


SHANGHAI = ZoneInfo("Asia/Shanghai")
MORNING = (time(9, 30), time(11, 30))
AFTERNOON = (time(13, 0), time(15, 0))
logger = logging.getLogger(__name__)


def _shanghai_datetime(value: datetime) -> datetime:
    """Treat naive values as Shanghai time; convert aware values to Shanghai."""
    if value.tzinfo is None:
        return value.replace(tzinfo=SHANGHAI)
    return value.astimezone(SHANGHAI)


def is_trading_time(value: datetime) -> bool:
    current = _shanghai_datetime(value)
    if current.weekday() >= 5:
        return False
    clock = current.time().replace(tzinfo=None)
    return MORNING[0] <= clock <= MORNING[1] or AFTERNOON[0] <= clock <= AFTERNOON[1]


def seconds_to_next_sample(value: datetime) -> float:
    """Return seconds to the next weekday five-minute trading bucket."""
    current = _shanghai_datetime(value)
    day = current.date()
    candidates: list[datetime] = []
    for offset in range(8):
        candidate_day = day + timedelta(days=offset)
        if candidate_day.weekday() >= 5:
            continue
        for start, end in (MORNING, AFTERNOON):
            bucket = datetime.combine(candidate_day, start, SHANGHAI)
            finish = datetime.combine(candidate_day, end, SHANGHAI)
            while bucket <= finish:
                if bucket > current:
                    candidates.append(bucket)
                    break
                bucket += timedelta(minutes=5)
        if candidates:
            break
    if not candidates:
        return 60.0
    return max(0.0, (min(candidates) - current).total_seconds())


async def _sample_ths() -> None:
    for sector_type in ("industry", "concept"):
        try:
            result = await asyncio.to_thread(list_sectors, sector_type, "ths")
            if not result.ok:
                logger.warning("同花顺%s板块采样失败：%s", sector_type, result.error)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("同花顺%s板块采样异常", sector_type)


async def run_etfline_sampler() -> None:
    while True:
        now = datetime.now(SHANGHAI)
        if is_trading_time(now):
            await _sample_ths()
            delay = seconds_to_next_sample(datetime.now(SHANGHAI))
        else:
            delay = 60.0
        await asyncio.sleep(max(delay, 0.1))
