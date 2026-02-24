"""MCP tool for indicator-based multi-symbol scanning."""

import re
from dataclasses import dataclass
from typing import Callable

from viper.mcp.server import mcp
from viper.services.history_data import HistoricalData, HistoricalDataError, fetch_historical_data
from viper.services.indicators import calculate_ema, calculate_macd, calculate_rsi, calculate_sma
from viper.services.watchlist import WatchlistManager

_RULE_RE = re.compile(
    r"^([A-Za-z_][A-Za-z0-9_]*)\s*(<=|>=|==|!=|<|>)\s*(-?\d+(?:\.\d+)?)$"
)


@dataclass(frozen=True)
class ScanRule:
    """A parsed rule expression."""

    raw: str
    field: str
    operator: str
    threshold: float


_COMPARATORS: dict[str, Callable[[float, float], bool]] = {
    "<": lambda x, y: x < y,
    "<=": lambda x, y: x <= y,
    ">": lambda x, y: x > y,
    ">=": lambda x, y: x >= y,
    "==": lambda x, y: x == y,
    "!=": lambda x, y: x != y,
}


def _last_valid(values: list[float | None]) -> float | None:
    """Return the last non-None value from a list."""
    for value in reversed(values):
        if value is not None:
            return value
    return None


def _parse_symbols(symbols: str) -> list[str]:
    """Parse comma/space separated symbols or 'watchlist' sentinel."""
    normalized = symbols.strip()
    if normalized.lower() == "watchlist":
        return WatchlistManager().get_all()
    return [s.upper() for s in re.split(r"[,\s]+", normalized) if s]


def _parse_rules(rules: str) -> tuple[list[ScanRule], str | None]:
    """Parse rule string into expressions."""
    parsed: list[ScanRule] = []
    chunks = [chunk.strip() for chunk in re.split(r"[;,]", rules) if chunk.strip()]
    if not chunks:
        return [], "No rules provided"

    for chunk in chunks:
        match = _RULE_RE.match(chunk)
        if not match:
            return [], (
                f"Invalid rule '{chunk}'. Expected format like 'rsi < 30' or 'sma20 > sma50' "
                "is not supported; use numeric thresholds."
            )
        field = match.group(1).lower()
        operator = match.group(2)
        threshold = float(match.group(3))
        parsed.append(ScanRule(raw=chunk, field=field, operator=operator, threshold=threshold))

    return parsed, None


def _compute_metrics(
    prices: list[float], rules: list[ScanRule], rsi_period: int
) -> dict[str, float | None]:
    """Compute only the metrics required by rules."""
    metrics: dict[str, float | None] = {"price": prices[-1] if prices else None}
    requested_fields = {rule.field for rule in rules}

    sma_periods = sorted(
        {
            int(field[3:])
            for field in requested_fields
            if field.startswith("sma") and field[3:].isdigit()
        }
    )
    for period in sma_periods:
        metrics[f"sma{period}"] = _last_valid(calculate_sma(prices, period))

    ema_periods = sorted(
        {
            int(field[3:])
            for field in requested_fields
            if field.startswith("ema") and field[3:].isdigit()
        }
    )
    for period in ema_periods:
        metrics[f"ema{period}"] = _last_valid(calculate_ema(prices, period))

    if "rsi" in requested_fields:
        metrics["rsi"] = _last_valid(calculate_rsi(prices, rsi_period))

    if requested_fields & {"macd_line", "macd_signal", "macd_histogram"}:
        macd_line, signal_line, histogram = calculate_macd(prices)
        metrics["macd_line"] = _last_valid(macd_line)
        metrics["macd_signal"] = _last_valid(signal_line)
        metrics["macd_histogram"] = _last_valid(histogram)

    return metrics


@mcp.tool()
async def get_scan(
    symbols: str,
    rules: str,
    period: str = "3M",
    rsi_period: int = 14,
) -> dict[str, object]:
    """Scan multiple symbols and return those matching indicator rules.

    Args:
        symbols: Comma or space-separated symbols (e.g. "AAPL,TSLA,BTC-USD") or "watchlist"
        rules: Rule expressions separated by ',' or ';', e.g. "rsi < 30; sma20 > 200"
        period: Historical data period - "1W", "1M", "3M", "6M", "1Y", "2Y", "5Y", "MAX"
        rsi_period: RSI lookback period (default 14)

    Returns:
        Symbols that match all rules, plus per-symbol errors.
    """
    symbol_list = _parse_symbols(symbols)
    if not symbol_list:
        return {"error": "No symbols to scan", "symbols": symbols}

    parsed_rules, rule_error = _parse_rules(rules)
    if rule_error is not None:
        return {"error": rule_error, "rules": rules}

    matches: list[dict[str, object]] = []
    errors: list[dict[str, str]] = []
    scanned = 0

    for symbol in symbol_list:
        result = await fetch_historical_data(symbol, period=period)
        if isinstance(result, HistoricalDataError):
            errors.append({"symbol": result.ticker, "error": result.error_message})
            continue

        assert isinstance(result, HistoricalData)
        scanned += 1
        metrics = _compute_metrics(result.prices, parsed_rules, rsi_period)

        rule_results: dict[str, bool] = {}
        matched_all = True
        for rule in parsed_rules:
            metric_value = metrics.get(rule.field)
            is_match = False
            if metric_value is not None:
                comparator = _COMPARATORS[rule.operator]
                is_match = comparator(metric_value, rule.threshold)
            rule_results[rule.raw] = is_match
            if not is_match:
                matched_all = False

        if matched_all:
            used_metrics = {rule.field: metrics.get(rule.field) for rule in parsed_rules}
            used_metrics["price"] = metrics.get("price")
            matches.append(
                {
                    "symbol": result.ticker,
                    "metrics": used_metrics,
                    "rule_results": rule_results,
                }
            )

    return {
        "period": period,
        "rules": [rule.raw for rule in parsed_rules],
        "symbols_requested": len(symbol_list),
        "symbols_scanned": scanned,
        "matched_count": len(matches),
        "matches": matches,
        "errors": errors,
    }
