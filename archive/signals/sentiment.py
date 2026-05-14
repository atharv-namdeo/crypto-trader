import requests


FEAR_GREED_URL = 'https://api.alternative.me/fng/?limit=1'


def fetch_fear_greed():
    """
    Fetch the latest Crypto Fear & Greed Index.
    Returns dict with value (0-100), classification, and timestamp.
    """
    try:
        resp = requests.get(FEAR_GREED_URL, timeout=10)
        data = resp.json()['data'][0]
        value = int(data['value'])
        classification = data['value_classification']
        return {
            'value': value,
            'classification': classification,
            'timestamp': data['timestamp'],
            'bias': _classify(value),
        }
    except Exception as e:
        print(f"[Sentiment] Failed to fetch Fear & Greed: {e}")
        return {'value': 50, 'classification': 'Neutral', 'bias': 'neutral'}


def _classify(value):
    """Map fear/greed score to a trading bias."""
    if value <= 25:
        return 'extreme_fear'   # contrarian bullish
    elif value <= 40:
        return 'fear'
    elif value <= 60:
        return 'neutral'
    elif value <= 75:
        return 'greed'
    else:
        return 'extreme_greed'  # contrarian bearish
