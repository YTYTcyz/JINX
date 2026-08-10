"""getkline 手动样例。

运行：
  python -m store_skill.test.test_getkline
"""

from store_skill.getkline import PERIODS, get_kline


def main() -> None:
    for period in PERIODS:
        result = get_kline("600519", period)
        count = len(result.data["items"]) if result.ok else 0
        print(f"{period:10} ok={result.ok} items={count} error={result.error}")


if __name__ == "__main__":
    main()
