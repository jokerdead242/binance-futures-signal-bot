import pandas as pd
import requests
import time
from datetime import datetime
from ta.trend import EMAIndicator, MACD, ADXIndicator
from ta.volatility import BollingerBands
from ta.momentum import RSIIndicator

# === Настройки ===
INTERVAL = "30m"
LIMIT = 200
SLEEP_TIME = 180  # 3 минуты
BINANCE_FUTURES_ENDPOINT = "https://fapi.binance.com"

# Цвета ANSI
def color_text(text, color):
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "cyan": "\033[96m",
        "end": "\033[0m"
    }
    return f"{colors[color]}{text}{colors['end']}"

# === Получение списка USDT-M фьючерсов (PERPETUAL) ===
def get_usdt_perpetual_symbols():
    url = f"{BINANCE_FUTURES_ENDPOINT}/fapi/v1/exchangeInfo"
    response = requests.get(url)
    symbols = []
    if response.status_code == 200:
        data = response.json()
        for symbol_info in data["symbols"]:
            if symbol_info["quoteAsset"] == "USDT" and symbol_info["contractType"] == "PERPETUAL":
                symbols.append(symbol_info["symbol"])
    return symbols

# === Получение исторических данных ===
def get_klines(symbol, interval, limit):
    url = f"{BINANCE_FUTURES_ENDPOINT}/fapi/v1/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        df = pd.DataFrame(data, columns=[
            "timestamp", "open", "high", "low", "close", "volume",
            "close_time", "quote_asset_volume", "number_of_trades",
            "taker_buy_base", "taker_buy_quote", "ignore"
        ])
        df["close"] = pd.to_numeric(df["close"])
        df["high"] = pd.to_numeric(df["high"])
        df["low"] = pd.to_numeric(df["low"])
        df["open"] = pd.to_numeric(df["open"])
        df["volume"] = pd.to_numeric(df["volume"])
        return df
    else:
        return None

# === Логика сигналов ===
def get_signal(df):
    if df is None or len(df) < 100:
        return "neutral"

    close = df["close"]

    try:
        ema = EMAIndicator(close, window=50).ema_indicator()
        macd_line = MACD(close).macd()
        rsi = RSIIndicator(close).rsi()
        bb = BollingerBands(close)
        adx = ADXIndicator(df["high"], df["low"], close)

        last_close = close.iloc[-1]
        last_ema = ema.iloc[-1]
        last_macd = macd_line.iloc[-1]
        last_rsi = rsi.iloc[-1]
        last_adx = adx.adx().iloc[-1]
        bb_upper = bb.bollinger_hband().iloc[-1]
        bb_lower = bb.bollinger_lband().iloc[-1]

        confirmations = 0
        if last_close > last_ema:
            confirmations += 1
        if last_macd > 0:
            confirmations += 1
        if last_rsi > 55:
            confirmations += 1
        if last_close < bb_upper:
            confirmations += 1
        if last_adx > 20:
            confirmations += 1
        if confirmations >= 3:
            return "long"

        confirmations = 0
        if last_close < last_ema:
            confirmations += 1
        if last_macd < 0:
            confirmations += 1
        if last_rsi < 45:
            confirmations += 1
        if last_close > bb_lower:
            confirmations += 1
        if last_adx > 20:
            confirmations += 1
        if confirmations >= 3:
            return "short"

        return "neutral"
    except:
        return "neutral"

# === Основной цикл ===
def run_scanner():
    print(color_text("Стартуем бесконечный сканер фьючерсов Binance USDT-M каждые 3 минуты", "cyan"))
    while True:
        print(f"\n=== СКАНИРОВАНИЕ: {datetime.now()} ===")
        print("Загружаем список рынков с Binance...")
        symbols = get_usdt_perpetual_symbols()
        print(f"Найдено {len(symbols)} PERPETUAL фьючерсов с котировкой в USDT.")

        for symbol in symbols:
            df = get_klines(symbol, INTERVAL, LIMIT)
            signal = get_signal(df)
            if signal == "long":
                print(f"{symbol}: {color_text('LONG', 'green')}")
            elif signal == "short":
                print(f"{symbol}: {color_text('SHORT', 'red')}")
            else:
                print(f"{symbol}: neutral")

        print(f"\nЖдем {SLEEP_TIME // 60} минут(ы) до следующего сканирования...\n")
        time.sleep(SLEEP_TIME)

# Для запуска раскомментируй строку ниже:
if __name__ == '__main__':
    run_scanner()