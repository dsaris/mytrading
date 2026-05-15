import requests
import pandas as pd
import urllib3

# ==========================================
# FIX SSL WARNING (biar aman di semua env)
# ==========================================
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ==========================================
# FUNCTION: Ambil data dari Binance
# ==========================================
def get_klines(symbol="BTCUSDT", interval="1h", limit=100):
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }

    response = requests.get(url, params=params, verify=False)
    data = response.json()

    df = pd.DataFrame(data, columns=[
        'time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'qav', 'trades', 'taker_base_vol',
        'taker_quote_vol', 'ignore'
    ])

    # Convert ke float
    df['close'] = df['close'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['volume'] = df['volume'].astype(float)

    return df


# ==========================================
# FUNCTION: Tambah indikator
# ==========================================
def add_indicators(df):
    df['ema50'] = df['close'].ewm(span=50).mean()

    df['volume_avg'] = df['volume'].rolling(20).mean()

    # Resistance (untuk breakout)
    df['resistance'] = df['close'].rolling(20).max()

    # Support (untuk SHORT)
    df['support'] = df['close'].rolling(20).min()

    # Range → untuk deteksi volatility (scalping)
    df['range'] = df['high'].rolling(20).max() - df['low'].rolling(20).min()

    return df


# ==========================================
# FUNCTION: SCORING SYSTEM (Versi 2)
# ==========================================
def score_trade(df):
    last = df.iloc[-1]
    score = 0

    # 1. Breakout / Breakdown (relevan untuk dua arah)
    if last['close'] > last['resistance'] * 0.995:
        score += 3

    if last['close'] < last['support'] * 1.005:
        score += 3

    # 2. Volume spike
    if last['volume'] > last['volume_avg']:
        score += 2

    # 3. Trend strength
    if last['close'] > last['ema50'] or last['close'] < last['ema50']:
        score += 2

    # 4. Volatility → peluang scalping
    if df['range'].iloc[-1] > df['range'].mean():
        score += 1

    return score


# ==========================================
# FUNCTION: DIRECTION SIGNAL (NEW CORE V3)
# ==========================================
def get_signal(df):
    last = df.iloc[-1]

    # ✅ LONG LOGIC
    if (
        last['close'] > last['ema50'] and
        last['close'] > last['resistance'] * 0.995 and
        last['volume'] > last['volume_avg']
    ):
        return "LONG"

    # ✅ SHORT LOGIC
    if (
        last['close'] < last['ema50'] and
        last['close'] < last['support'] * 1.005 and
        last['volume'] > last['volume_avg']
    ):
        return "SHORT"

    return "NO TRADE"


# ==========================================
# MAIN PROGRAM
# ==========================================

pairs = [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "XRPUSDT",
    "DOGEUSDT"
]

results = []

for pair in pairs:
    try:
        df = get_klines(pair)
        df = add_indicators(df)

        score = score_trade(df)
        signal = get_signal(df)

        results.append((pair, score, signal))

    except Exception as e:
        print(f"Error di {pair}: {e}")


# Sort berdasarkan score tertinggi
results = sorted(results, key=lambda x: x[1], reverse=True)


# ==========================================
# OUTPUT FINAL
# ==========================================
print("\n=== HASIL SCANNER V3 ===")

for pair, score, signal in results:

    # Status strength
    if score >= 6:
        status = "✅ STRONG"
    elif score >= 4:
        status = "⚠️ MEDIUM"
    else:
        status = "❌ WEAK"

    print(f"{pair} → Score: {score} {status} | Signal: {signal}")
