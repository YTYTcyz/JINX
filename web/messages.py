"""Convert data-source errors into user-friendly Chinese messages."""


SOURCE_NAMES = {
    "eastmoney": "东方财富",
    "sina": "新浪财经",
    "xueqiu": "雪球",
    "tushare": "Tushare",
}

ERROR_MESSAGES = (
    ("empty response", "未返回数据，可能暂时限流或该代码不受支持"),
    ("No value to decode", "返回内容无法解析，数据源可能暂时异常"),
    ("Remote end closed connection", "数据源主动断开连接，可能请求过于频繁"),
    ("Connection aborted", "连接被中断，请稍后重试"),
    ("timed out", "请求超时，请稍后重试"),
    ("missing price", "未返回有效价格"),
    ("no parseable quotes", "返回的行情数据无法解析"),
    ("blocked or empty response", "请求被限制或没有返回数据"),
    ("no data", "暂时没有该代码的行情数据"),
    ("unsupported stock symbol", "股票代码格式不正确"),
    ("unsupported period", "不支持这个时间周期"),
)


def friendly_error(error: str | None) -> str:
    if not error:
        return "发生未知错误，请稍后重试"

    translated = []
    for part in error.split(" | "):
        source, separator, detail = part.partition(": ")
        has_source = bool(separator and source in SOURCE_NAMES)
        source_name = SOURCE_NAMES.get(source, source)
        text = detail if has_source else part

        message = next(
            (chinese for keyword, chinese in ERROR_MESSAGES if keyword in text),
            f"请求失败（{text}）",
        )
        translated.append(f"{source_name}：{message}" if has_source else message)

    return "；".join(translated)
