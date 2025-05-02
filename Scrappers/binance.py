import requests
import time
import logging
from Src.fiat_prices import get_exchange_rate

BINANCE_P2P_URL = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"

class BinanceScraper:
    name = "binance"
    supported_fiats =["NGN", "USD", "EUR", "BRL", "KES", "GBP", "CAD", "AUD"]
    
    def fetch_data(self, asset="USDT", fiat="USD", trade_type="BUY", page=1, rows=10):
        payload = {
            "page": page,
            "rows": rows,
            "payTypes": [],
            "asset": asset,
            "fiat": fiat,
            "tradeType": trade_type
        }
        headers = {"Content-Type": "application/json"}
        try:
            response = requests.post(BINANCE_P2P_URL, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Error fetching Binance P2P data for {fiat} ({trade_type}): {e}")
            return None
    
    def get_best_prices(self, fiat):
        best_buy, best_sell = None, None
        best_buy_merchant, best_sell_merchant = "Unknown", "Unknown"
        
        # Fetch BUY offers
        buy_data = self.fetch_data(asset="USDT", fiat=fiat, trade_type="BUY", page=1, rows=10)
        buy_prices = []
        buy_merchants = {}
        if buy_data and "data" in buy_data:
            for adv in buy_data["data"]:
                price = adv.get("adv", {}).get("price")
                merchant_name = adv.get("advertiser", {}).get("nickName", "Unknown")
                if price:
                    try:
                        float_price = float(price)
                        buy_prices.append(float_price)
                        buy_merchants[float_price] = merchant_name
                    except ValueError:
                        continue
        if buy_prices:
            best_buy = min(buy_prices)
            best_buy_merchant = buy_merchants.get(best_buy, "Unknown")
        
        
        sell_data = self.fetch_data(asset="USDT", fiat=fiat, trade_type="SELL", page=1, rows=10)
        sell_prices = []
        sell_merchants = {}
        if sell_data and "data" in sell_data:
            for adv in sell_data["data"]:
                price = adv.get("adv", {}).get("price")
                merchant_name = adv.get("advertiser", {}).get("nickName", "Unknown")
                if price:
                    try:
                        float_price = float(price)
                        sell_prices.append(float_price)
                        sell_merchants[float_price] = merchant_name
                    except ValueError:
                        continue
        if sell_prices:
            best_sell = max(sell_prices)
            best_sell_merchant = sell_merchants.get(best_sell, "Unknown")
        
        return best_buy, best_sell, best_buy_merchant, best_sell_merchant
