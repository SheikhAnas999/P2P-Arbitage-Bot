from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys 
import time
import logging
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, ElementClickInterceptedException


class OKXScraper:
    name = "okx"
    supported_fiats = ["NGN", "USD", "EUR", "BRL", "KES", "GBP", "CAD", "AUD"]
    
    def __init__(self):
        self.logger = logging.getLogger("OKXScraper")
    
    def get_best_prices(self, fiat):
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--log-level=3")
        
        driver = webdriver.Chrome(options=chrome_options)
        
        try:
            wait = WebDriverWait(driver, 20)
            driver.get("https://www.okx.com/p2p-markets")
            time.sleep(5)
            driver.refresh()
            time.sleep(5)
            
            data_rows = []
            
            def scrape_and_collect(price_type):
                nonlocal driver, wait, data_rows, fiat
                page_num = 1
                max_pages = 2
                has_next_page = True
                while has_next_page and page_num <= max_pages:
                    try:
                        price_wait = WebDriverWait(driver, 15)
                        prices = price_wait.until(EC.presence_of_all_elements_located((By.XPATH, "//span[@class='price']")))
                        merchants = driver.find_elements(By.XPATH, "//a[contains(@class, 'Tags_merchantLink__u5a8b')]")
                        if prices:
                            self.logger.info(f"Scraped {len(prices)} prices on page {page_num} for {price_type}")
                            for i, price_element in enumerate(prices):
                                try:
                                    price_text = price_element.text.strip()
                                    merchant_name = merchants[i].text.strip() if i < len(merchants) else "N/A"
                                    if price_text:
                                        data_rows.append({
                                            'Currency': fiat,
                                            'PriceType': price_type,
                                            'Price': price_text,
                                            'Merchant': merchant_name,
                                            'Page': page_num
                                        })
                                except StaleElementReferenceException:
                                    continue
                        else:
                            self.logger.info(f"No prices found on page {page_num} for {price_type}")
                        
                        if page_num >= max_pages:
                            break
                        next_buttons = driver.find_elements(By.XPATH, "//li[@class='okui-pagination-next']")
                        if next_buttons:
                            next_button = next_buttons[0]
                            if next_button.is_displayed() and 'disabled' not in next_button.get_attribute('class'):
                                driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                                time.sleep(1)
                                driver.execute_script("arguments[0].click();", next_button)
                                page_num += 1
                                time.sleep(5)
                            else:
                                has_next_page = False
                        else:
                            has_next_page = False
                    except Exception as e:
                        self.logger.error(f"Exception in scrape_and_collect: {e}")
                        has_next_page = False
            
            # Select the fiat currency via dropdown
            dropdown_xpath = "(//div[@class='okui-input-box auto-size okui-select-inner-box'])[2]"
            search_box_xpath = "//input[@class='okui-input-input okui-select-search-ellipsis']"
            active_item_xpath = "(//div[@class='flex items-center gap-1 md:gap-2'])[3]"
            
            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    dropdown = wait.until(EC.element_to_be_clickable((By.XPATH, dropdown_xpath)))
                    driver.execute_script("arguments[0].scrollIntoView(true);", dropdown)
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", dropdown)
                    WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.XPATH, search_box_xpath)))
                    break
                except Exception as e:
                    self.logger.error(f"Attempt {attempt+1} to click dropdown failed: {e}")
                    if attempt == max_attempts - 1:
                        raise e
                    time.sleep(2)
            
            search_box = wait.until(EC.visibility_of_element_located((By.XPATH, search_box_xpath)))
            search_box.clear()
            search_box.send_keys(Keys.CONTROL + "a")
            search_box.send_keys(Keys.DELETE)
            driver.execute_script("arguments[0].value = '';", search_box)
            time.sleep(1)
            for char in fiat:
                search_box.send_keys(char)
                time.sleep(0.1)
            time.sleep(2)
            active_item = wait.until(EC.element_to_be_clickable((By.XPATH, active_item_xpath)))
            driver.execute_script("arguments[0].click();", active_item)
            self.logger.info(f"Selected fiat currency: {fiat}")
            time.sleep(5)
            
            # Scrape Buy and Sell Offers
            buy_tab_xpath = "//a[contains(@class,'side-item') and contains(@href,'buy-usdt') and text()='Buy']"
            sell_tab_xpath = "//a[contains(@class,'side-item') and contains(@href,'sell-usdt') and text()='Sell']"
            
            buy_tab = wait.until(EC.element_to_be_clickable((By.XPATH, buy_tab_xpath)))
            driver.execute_script("arguments[0].click();", buy_tab)
            self.logger.info("Clicked Buy tab")
            time.sleep(5)
            scrape_and_collect("Buy")
            
            sell_tab = wait.until(EC.element_to_be_clickable((By.XPATH, sell_tab_xpath)))
            driver.execute_script("arguments[0].click();", sell_tab)
            self.logger.info("Clicked Sell tab")
            time.sleep(5)
            scrape_and_collect("Sell")
            
            self.logger.info(f"Data rows collected: {data_rows}")
            
            buy_prices = []
            sell_prices = []
            buy_merchants = {}
            sell_merchants = {}
            for row in data_rows:
                try:
                    price_numeric = row['Price'].split()[0]
                    price_val = float(price_numeric.replace(',', ''))
                    if row['PriceType'] == "Buy":
                        buy_prices.append(price_val)
                        buy_merchants[price_val] = row['Merchant']
                    elif row['PriceType'] == "Sell":
                        sell_prices.append(price_val)
                        sell_merchants[price_val] = row['Merchant']
                except Exception as ex:
                    self.logger.error(f"Error processing row {row}: {ex}")
                    continue
            
            best_buy = min(buy_prices) if buy_prices else None
            best_sell = max(sell_prices) if sell_prices else None
            best_buy_merchant = buy_merchants.get(best_buy, "Unknown") if best_buy is not None else "Unknown"
            best_sell_merchant = sell_merchants.get(best_sell, "Unknown") if best_sell is not None else "Unknown"
            
            return best_buy, best_sell, best_buy_merchant, best_sell_merchant
            
        except Exception as e:
            self.logger.error(f"Error in get_best_prices: {e}")
            return None, None, "Unknown", "Unknown"
        finally:
            driver.quit()
           
