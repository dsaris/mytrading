
import requests
import pandas as pd
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# GET TOP FUTURES (BERDASARKAN VOLUME)
# ==========================================
def get_top_pairs(limit=20):
    url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
    
    data = requests.get(url, verify=False).json()

    df = pd.DataFrame(data)

    # Filter hanya USDT pairs
    df = df[df['symbol'].str.endswith('USDT')]

    # Convert volume
    df['quoteVolume'] = df['quoteVolume'].astype(float)

    # Sort by volume terbesar
    df = df.sort_values(by='quoteVolume', ascending=False)

    # Ambil top N
    top_pairs = df['symbol'].head(limit).tolist()

    return top_pairs


# ==========================================
# GET KLINES
# ==========================================
def get_klines(symbol="BTCUSDT", interval="1h", limit=100):
    url = "https://fapi.binance.com/fapi/v1/klines"
    
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }

    response = requests.get(url, params=params, verify=False)
    data = response.json()

    df = pd.DataFrame(data, columns=[
        'time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'qav', 'trades',
        'taker_base_vol', 'taker_quote_vol', 'ignore'
    ])

    df['close'] = df['close'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['volume'] = df['volume'].astype(float)

    return df


# ==========================================
# INDICATORS
# ==========================================
def add_indicators(df):
    df['ema50'] = df['close'].ewm(span=50).mean()
    df['volume_avg'] = df['volume'].rolling(20).mean()

    df['resistance'] = df['close'].rolling(20).max()
    df['support'] = df['close'].rolling(20).min()

    df['range'] = df['high'].rolling(20).max() - df['low'].rolling(20).min()

    return df


# ==========================================
# SCORING
# ==========================================
def score_trade(df):
    last = df.iloc[-1]
    score = 0

    # Breakout / Breakdown
    if last['close'] > last['resistance'] * 0.995:
        score += 3
    if last['close'] < last['support'] * 1.005:
        score += 3

    # Volume
    if last['volume'] > last['volume_avg']:
        score += 2

    # Trend
    if last['close'] > last['ema50'] or last['close'] < last['ema50']:
        score += 2

    # Volatility
    if df['range'].iloc[-1] > df['range'].mean():
        score += 1

    return score


# ==========================================
# SIGNAL (LONG / SHORT)
# ==========================================
def get_signal(df):
    last = df.iloc[-1]

    # LONG
    if (
        last['close'] > last['ema50'] and
        last['close'] > last['resistance'] * 0.995 and
        last['volume'] > last['volume_avg']
    ):
        return "LONG"

    # SHORT
    if (
        last['close'] < last['ema50'] and
        last['close'] < last['support'] * 1.005 and
        last['volume'] > last['volume_avg']
    ):
        return "SHORT"

    # POTENTIAL
    if last['close'] > last['ema50']:
        return "POTENTIAL LONG"
    elif last['close'] < last['ema50']:
        return "POTENTIAL SHORT"

    return "NO TRADE"


# ==========================================
# MAIN
# ==========================================

print("Mengambil top futures pairs...")
pairs = get_top_pairs(20)

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

# Sort hasil
results = sorted(results, key=lambda x: x[1], reverse=True)

# ==========================================
# OUTPUT
# ==========================================
print("\n=== TOP 20 FUTURES SCANNER ===")

for pair, score, signal in results:

    if score >= 6:
        status = "✅ STRONG"
    elif score >= 4:
        status = "⚠️ MEDIUM"
    else:
        status = "❌ WEAK"

    print(f"{pair} → Score: {score} {status} | Signal: {signal}")
