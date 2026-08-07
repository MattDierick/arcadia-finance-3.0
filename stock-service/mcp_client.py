"""
mcp_client.py – Thin async wrapper around the yahoo-finance-mcp stdio server.

Spawns vendor/server.py as a subprocess per call, communicates via the MCP
stdio transport, invokes the requested tool, returns the parsed result.

Attribution: vendor/server.py is © Alex2Yang97/yahoo-finance-mcp (MIT licence).
"""

import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Absolute path to the vendored MCP server script
_VENDOR_SERVER = os.path.join(os.path.dirname(__file__), "vendor", "server.py")


async def _call_tool(tool_name: str, arguments: dict) -> str:
    """
    Open a stdio MCP session, call one tool, close the session.
    Returns the raw text content string produced by the tool.
    """
    server_params = StdioServerParameters(
        command=sys.executable,          # same Python interpreter
        args=[_VENDOR_SERVER],
        env=None,                        # inherit current environment
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments=arguments)
            # FastMCP tools return a list of TextContent; extract the first text
            if result.content and hasattr(result.content[0], "text"):
                return result.content[0].text
            return ""


def call_tool(tool_name: str, arguments: dict) -> str:
    """Synchronous wrapper – runs the async helper in a fresh event loop."""
    return asyncio.run(_call_tool(tool_name, arguments))


# ── Convenience helpers ───────────────────────────────────────────────────────

def get_stock_info(ticker: str) -> dict:
    """
    Return a normalised quote dict extracted from get_stock_info.
    Keys guaranteed: ticker, name, price, currency, exchange,
                     change, change_pct, market_cap, pe_ratio, volume.
    """
    raw = call_tool("get_stock_info", {"ticker": ticker.upper()})

    # The tool returns a JSON string or an error message
    try:
        info = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        if raw and raw.startswith("Company ticker"):
            raise ValueError(raw)
        raise ValueError(f"Unexpected response from MCP server: {raw!r}")

    if not isinstance(info, dict):
        raise ValueError(f"Unexpected data shape from get_stock_info: {type(info)}")

    # yfinance uses different price keys depending on market state
    price = (
        info.get("currentPrice")
        or info.get("regularMarketPrice")
        or info.get("previousClose")
        or 0.0
    )
    prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose") or price
    change = round(float(price) - float(prev_close), 4) if prev_close else 0.0
    change_pct = round((change / float(prev_close)) * 100, 2) if prev_close else 0.0

    return {
        "ticker":       ticker.upper(),
        "name":         info.get("shortName") or info.get("longName") or ticker.upper(),
        "price":        float(price),
        "currency":     info.get("currency", "USD"),
        "exchange":     info.get("exchange") or info.get("fullExchangeName", ""),
        "change":       change,
        "change_pct":   change_pct,
        "market_cap":   info.get("marketCap"),
        "pe_ratio":     info.get("trailingPE") or info.get("forwardPE"),
        "volume":       info.get("volume") or info.get("regularMarketVolume"),
        "day_high":     info.get("dayHigh") or info.get("regularMarketDayHigh"),
        "day_low":      info.get("dayLow") or info.get("regularMarketDayLow"),
        "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
        "fifty_two_week_low":  info.get("fiftyTwoWeekLow"),
        "sector":       info.get("sector"),
        "industry":     info.get("industry"),
    }


def get_historical_prices(ticker: str, period: str = "1mo", interval: str = "1d") -> list:
    """
    Return OHLCV records as a list of dicts.
    Each dict has: date, open, high, low, close, volume.
    """
    raw = call_tool(
        "get_historical_stock_prices",
        {"ticker": ticker.upper(), "period": period, "interval": interval},
    )
    try:
        records = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        raise ValueError(f"Cannot parse history for {ticker}: {raw!r}")

    if not isinstance(records, list):
        raise ValueError(f"Unexpected history shape: {type(records)}")

    cleaned = []
    for r in records:
        # Date key varies: "Date", "Datetime", or epoch ms integer (from orient="records")
        date_val = r.get("Date") or r.get("Datetime") or r.get("index")
        if isinstance(date_val, (int, float)):
            # millisecond epoch → ISO string
            import datetime
            date_val = datetime.datetime.utcfromtimestamp(date_val / 1000).strftime("%Y-%m-%d")
        cleaned.append({
            "date":   str(date_val)[:10] if date_val else None,
            "open":   r.get("Open"),
            "high":   r.get("High"),
            "low":    r.get("Low"),
            "close":  r.get("Close"),
            "volume": r.get("Volume"),
        })
    return cleaned
