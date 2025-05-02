import requests
import logging

logger = logging.getLogger("FiatPrices")

def get_exchange_rate(fiat):
    fiat = fiat.upper()
    if fiat == "USD":
        return 1.0
    url = "https://open.er-api.com/v6/latest/USD"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        rate = data.get("rates", {}).get(fiat)
        if rate is None:
            logger.warning(f"No exchange rate found for {fiat}")
        return rate
    except Exception as e:
        logger.error(f"Error fetching exchange rate for {fiat}: {e}")
        return None
