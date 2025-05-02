import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import datetime
import logging
import sys
import setuptools._distutils as distutils
sys.modules["distutils"] = distutils


class PaxfulScraper:
    name = "paxful"
    supported_fiats = ["NGN", "USD", "EUR", "BRL", "KES", "GBP", "CAD", "AUD"]
    
    def __init__(self):
        self.logger = logging.getLogger("PaxfulScraper")
    
    def scrape_prices(self, driver, url, currencies, trade_type):
        results_data = {
            'Currency': [],
            'Price': [],
            'Trade_Type': [],
            'Date_Scraped': [],
            'Merchant_Name': []
        }
        current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.logger.info(f"Navigating to {url} to scrape {trade_type} prices...")
        driver.get(url)
        time.sleep(3)
        
        self.logger.info("Clicking country selection button...")
        country_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH,
                "//button[@class='qa-search-country-cta d-flex align-items-center btn-square btn btn-light btn-lg btn-block']"))
        )
        country_button.click()
        
        self.logger.info("Selecting 'Worldwide' option...")
        worldwide_option = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH,
                "//div[@data-testid='searchable-select-option-text' and text()='Worldwide']"))
        )
        worldwide_option.click()
        
        for currency in currencies:
            self.logger.info(f"Processing currency: {currency} for {trade_type}")
            secondary_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH,
                    "//button[@class='_0nTtV btn btn-outline-secondary btn-md']"))
            )
            secondary_button.click()
            time.sleep(5)
            
            self.logger.info("Clicking currency container to focus input...")
            currency_container = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH,
                    "//*[contains(@class, 'css-z89e5k') and contains(@class, 'text-gray-600') and contains(@class, 'label-md')]"))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", currency_container)
            driver.execute_script("arguments[0].click();", currency_container)
            time.sleep(1)
            
            self.logger.info("Locating currency input element...")
            currency_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH,
                    "//div[contains(@class, 'css')]//div[contains(@class, 'text-gray-900')]//input"))
            )
            currency_input.clear()
            currency_input.send_keys(currency)
            time.sleep(1)
            
            self.logger.info("Selecting specific currency option...")
            currency_option = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH,
                    "//div[contains(@class,'css')]//div[@class='d-flex justify-content-between align-items-center w-100 label-md']"))
            )
            currency_option.click()
            
            self.logger.info("Clicking Find Offers...")
            find_option = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH,
                    "//button[@class='d-flex align-items-center w-100 justify-content-between btn btn-primary btn-lg']"))
            )
            find_option.click()
            self.logger.info("Waiting for results to load...")
            time.sleep(8)
            
            self.logger.info(f"Scraping {trade_type} prices for {currency}...")
            try:
                price_elements = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.XPATH, "//p[@class='JYvOZ text-right m-0']"))
                )
                merchant_elements = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.XPATH, "//a[@class='DKSO-']"))
                )
                if price_elements:
                    self.logger.info(f"Found {len(price_elements)} {trade_type} price entries for {currency}")
                    for i, price_element in enumerate(price_elements):
                        price_text = price_element.text.strip()
                        merchant_name = merchant_elements[i].text.strip() if i < len(merchant_elements) else "Unknown"
                        results_data['Currency'].append(currency)
                        results_data['Price'].append(price_text)
                        results_data['Trade_Type'].append(trade_type)
                        results_data['Date_Scraped'].append(current_date)
                        results_data['Merchant_Name'].append(merchant_name)
                        self.logger.info(f"Recorded {trade_type} price: {price_text}, Merchant: {merchant_name}")
                else:
                    self.logger.warning(f"No {trade_type} price data found for {currency}")
            except Exception as e:
                self.logger.error(f"Error scraping {trade_type} prices for {currency}: {str(e)}")
            time.sleep(2)
        
        return results_data
    
    def extract_best_prices(self, all_prices, currency):
        buy_prices = []
        sell_prices = []
        buy_merchants = {}
        sell_merchants = {}
        
        for i in range(len(all_prices['Currency'])):
            if all_prices['Currency'][i] == currency:
                price_str = all_prices['Price'][i]
                try:
                    price_clean = ''.join(c for c in price_str if c.isdigit() or c == '.')
                    price = float(price_clean)
                    if all_prices['Trade_Type'][i] == 'BUY':
                        buy_prices.append(price)
                        buy_merchants[price] = all_prices['Merchant_Name'][i]
                    elif all_prices['Trade_Type'][i] == 'SELL':
                        sell_prices.append(price)
                        sell_merchants[price] = all_prices['Merchant_Name'][i]
                except ValueError:
                    continue
        
        best_buy = min(buy_prices) if buy_prices else None
        best_sell = max(sell_prices) if sell_prices else None
        best_buy_merchant = buy_merchants.get(best_buy, "Unknown") if best_buy is not None else "Unknown"
        best_sell_merchant = sell_merchants.get(best_sell, "Unknown") if best_sell is not None else "Unknown"
        return best_buy, best_sell, best_buy_merchant, best_sell_merchant
    
    def get_best_prices(self, fiat):

        
        # Launch Chrome in headless mode.
        driver = uc.Chrome(headless=False)
        try:
            currencies = [fiat]
            buy_results = self.scrape_prices(driver, "https://paxful.com/buy-tether/", currencies, "BUY")
            sell_results = self.scrape_prices(driver, "https://paxful.com/sell-tether/", currencies, "SELL")
            all_results = {
                'Currency': buy_results['Currency'] + sell_results['Currency'],
                'Price': buy_results['Price'] + sell_results['Price'],
                'Trade_Type': buy_results['Trade_Type'] + sell_results['Trade_Type'],
                'Date_Scraped': buy_results['Date_Scraped'] + sell_results['Date_Scraped'],
                'Merchant_Name': buy_results['Merchant_Name'] + sell_results['Merchant_Name']
            }
            return self.extract_best_prices(all_results, fiat)
        except Exception as e:
            self.logger.error(f"Error in get_best_prices: {e}")
            return None, None, "Unknown", "Unknown"
        finally:
            driver.quit()

