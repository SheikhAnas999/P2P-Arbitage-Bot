import logging
from datetime import datetime
from Src.fiat_prices import get_exchange_rate
from Scrappers.binance import BinanceScraper
from Scrappers.paxful import PaxfulScraper
from Scrappers.remitano import RemitanoScraper
from Scrappers.okx import OKXScraper
import sys


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
         logging.FileHandler("app.log", encoding="utf-8"),
         logging.StreamHandler()
    ]
)

def main():
    logging.info("Starting crypto P2P price comparison for arbitrage opportunities.")
    
    fiat_currencies = ["NGN", "USD", "EUR", "BRL", "KES", "GBP", "CAD", "AUD"]
    
    scrapers = [
        BinanceScraper(),
        OKXScraper(),
        PaxfulScraper(),
        RemitanoScraper(),
        
        
    ]
    
    buy_opportunities = []  
    sell_opportunities = [] 
    
    for scraper in scrapers:
        for fiat in fiat_currencies:
            if fiat not in scraper.supported_fiats:
                logging.info(f"Skipping {fiat} for {scraper.name} (unsupported fiat).")
                continue
            
            logging.info(f"Fetching {scraper.name} prices for {fiat}.")
            best_buy, best_sell, best_buy_merchant, best_sell_merchant = scraper.get_best_prices(fiat)
            
            if best_buy is None and best_sell is None:
                logging.info(f"No offers found for {fiat} on {scraper.name}.")
                continue
            
            rate = get_exchange_rate(fiat)
            if rate is None:
                logging.warning(f"Skipping conversion for {fiat} due to missing exchange rate.")
                continue
            
            usd_buy = best_buy / rate if best_buy is not None else None
            usd_sell = best_sell / rate if best_sell is not None else None

            if usd_buy is not None:
                logging.info(f"{scraper.name} {fiat} BUY: {best_buy} {fiat} (≈{usd_buy:.3f} USD), Merchant={best_buy_merchant}")
                buy_opportunities.append({
                    "exchange": scraper.name,
                    "fiat": fiat,
                    "price": best_buy,
                    "usd": usd_buy,
                    "merchant": best_buy_merchant
                })
            if usd_sell is not None:
                logging.info(f"{scraper.name} {fiat} SELL: {best_sell} {fiat} (≈{usd_sell:.3f} USD), Merchant={best_sell_merchant}")
                sell_opportunities.append({
                    "exchange": scraper.name,
                    "fiat": fiat,
                    "price": best_sell,
                    "usd": usd_sell,
                    "merchant": best_sell_merchant
                })
    
    best_trade = None
    best_profit_pct = 0.0
    profitable_trades = []  
    
    for buy in buy_opportunities:
        for sell in sell_opportunities:
            if buy["exchange"] == sell["exchange"]:
                continue
            profit = sell["usd"] - buy["usd"]
            if profit <= 0:
                continue
            profit_pct = (profit / buy["usd"]) * 100
            
            if profit_pct >= 50.0:
                profitable_trades.append({
                    "buy": buy,
                    "sell": sell,
                    "profit_pct": profit_pct,
                    "profit_usd": profit
                })
                
            if profit_pct > best_profit_pct:
                best_profit_pct = profit_pct
                best_trade = {
                    "buy": buy,
                    "sell": sell,
                    "profit_pct": profit_pct,
                    "profit_usd": profit
                }
    
    profitable_trades.sort(key=lambda x: x["profit_pct"], reverse=True)
    
    print("\n\n========== Arbitrage Opportunities ==========")
    if best_trade:
        print(f"Found {len(profitable_trades)} arbitrage opportunities with 50%+ profit:")
        
        for i, trade in enumerate(profitable_trades, 1):
            buy = trade["buy"]
            sell = trade["sell"]
            print(f"\n--- Opportunity #{i} (Profit: {trade['profit_pct']:.2f}%) ---")
            print(f"[BUY] {buy['exchange']}: 1 USDT = {buy['price']} {buy['fiat']} (≈{buy['usd']:.3f} USD), Merchant={buy['merchant']}")
            print(f"[SELL] {sell['exchange']}: 1 USDT = {sell['price']} {sell['fiat']} (≈{sell['usd']:.3f} USD), Merchant={sell['merchant']}")
            print(f"Net Profit: +{trade['profit_pct']:.2f}% per trade (≈{trade['profit_usd']:.3f} USD)")
    else:
        print("No arbitrage opportunities found.")
    print("===========================================\n")

if __name__ == "__main__":
    main()
