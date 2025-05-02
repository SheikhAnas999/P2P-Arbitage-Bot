from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import logging
from selenium.common.exceptions import StaleElementReferenceException

class RemitanoScraper:
    name = "remintano"
    supported_fiats = ["NGN", "USD", "EUR", "BRL", "KES", "GBP", "CAD", "AUD"]
    
    def __init__(self):
        self.logger = logging.getLogger("RemitanoScraper")
    
    def scrape(self, driver, url, trade_type, currencies):
        driver.get(url)
        wait = WebDriverWait(driver, 20)
        time.sleep(5)
        
        pop_up_xpath = "//button[@role='button']//div[@dir='auto' and contains(@class,'css-146c3p1') and normalize-space(text())='Close']"
        target_xpath = "(//div[@class='css-175oi2r r-1loqt21 r-1otgn73'])[10]"
        price_xpath = "//h6[@class='css-146c3p1 r-1loqt21']"
        merchant_xpath = "//a[contains(@href, '/global/profile')]/div[@class='css-175oi2r']/div[@class='css-146c3p1']"
        
        all_prices = {}
        
        try:
            pop_up_elem = wait.until(EC.element_to_be_clickable((By.XPATH, pop_up_xpath)))
            pop_up_elem.click()
            self.logger.info(f"Pop-up found and removed on {trade_type} page.")
        except Exception as e:
            self.logger.info(f"Pop-up not found or not clickable on {trade_type} page.")
           
        try:
            time.sleep(2)
            target_elem = wait.until(EC.element_to_be_clickable((By.XPATH, target_xpath)))
            driver.execute_script("arguments[0].scrollIntoView(true);", target_elem)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", target_elem)
            self.logger.info(f"Clicked on currency selector on {trade_type} page.")
            time.sleep(2)
        except Exception as e:
            self.logger.error(f"Currency selector button not found or not clickable on {trade_type} page: {e}")
            return all_prices
        
        for currency in currencies:
            try:
                self.logger.info(f"Processing currency: {currency} for {trade_type}")
                time.sleep(3)
                currency_xpath = f"//div[@data-testid='dropdown-menu-item fiat-currency-option-{currency}']"
                currency_elem = wait.until(EC.element_to_be_clickable((By.XPATH, currency_xpath)))
                driver.execute_script("arguments[0].scrollIntoView(true);", currency_elem)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", currency_elem)
                self.logger.info(f"Selected currency: {currency}")
                time.sleep(5)
                
                try:
                    price_elements = wait.until(EC.presence_of_all_elements_located((By.XPATH, price_xpath)))
                    merchant_elements = wait.until(EC.presence_of_all_elements_located((By.XPATH, merchant_xpath)))
                    entries = []
                    if price_elements:
                        self.logger.info(f"Found {len(price_elements)} price elements for {currency} on {trade_type} page")
                        for i, price_element in enumerate(price_elements):
                            try:
                                price_text = price_element.text.strip().replace(',', '')
                                merchant_name = "Unknown"
                                if i < len(merchant_elements):
                                    merchant_name = merchant_elements[i].text.strip()
                                if price_text and merchant_name and merchant_name.lower() != "unknown":
                                    self.logger.info(f"{currency}: {price_text}, Merchant: {merchant_name}")
                                    entries.append((price_text, merchant_name))
                            except StaleElementReferenceException:
                                self.logger.warning("Stale element reference encountered, skipping this price")
                                continue
                            except Exception as e:
                                self.logger.error(f"Error processing price: {e}")
                                continue
                        if entries:
                            all_prices[currency] = entries
                            self.logger.info(f"Extracted {len(entries)} valid prices for {currency} on {trade_type} page")
                        else:
                            self.logger.info(f"No valid price entries found for {currency} on {trade_type} page")
                    else:
                        self.logger.info(f"No price elements found for {currency} on {trade_type} page")
                except Exception as e:
                    self.logger.error(f"Error extracting data for {currency} on {trade_type} page: {e}")
                
                if currency != currencies[-1]:
                    target_elem = wait.until(EC.element_to_be_clickable((By.XPATH, target_xpath)))
                    driver.execute_script("arguments[0].scrollIntoView(true);", target_elem)
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", target_elem)
                    self.logger.info(f"Reopened currency selector for next currency on {trade_type} page.")
                    time.sleep(2)
                    
            except Exception as e:
                self.logger.error(f"Error processing currency '{currency}' on {trade_type} page: {e}")
        
        return all_prices
    
    def get_best_prices(self, fiat):

        
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--log-level=3")
        
        driver = webdriver.Chrome(options=chrome_options)
        try:
            currencies = [fiat]
            buy_prices = self.scrape(driver, "https://remitano.com/global/p2p/usdt/buy", "BUY", currencies)
            sell_prices = self.scrape(driver, "https://remitano.com/global/p2p/usdt/sell", "SELL", currencies)
            
            def convert_prices(entries):
                converted = []
                for price, merchant in entries:
                    try:
                        converted.append((float(price), merchant))
                    except:
                        continue
                return converted
            
            buy_entries = convert_prices(buy_prices.get(fiat, []))
            sell_entries = convert_prices(sell_prices.get(fiat, []))
            
            best_buy = min(buy_entries, key=lambda x: x[0])[0] if buy_entries else None
            best_sell = max(sell_entries, key=lambda x: x[0])[0] if sell_entries else None
            
            best_buy_merchant = "Unknown"
            best_sell_merchant = "Unknown"
            
            if best_buy is not None:
                for price, merchant in buy_entries:
                    if price == best_buy:
                        best_buy_merchant = merchant
                        break
            if best_sell is not None:
                for price, merchant in sell_entries:
                    if price == best_sell:
                        best_sell_merchant = merchant
                        break
            
            return best_buy, best_sell, best_buy_merchant, best_sell_merchant
        except Exception as e:
            self.logger.error(f"Error in get_best_prices: {e}")
            return None, None, "Unknown", "Unknown"
        finally:
            driver.quit()
    
