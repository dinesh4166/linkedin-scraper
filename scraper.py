import os
import pickle
import time
import pandas as pd
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
import os
load_dotenv()   

LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD")

# LinkedIn credentials (keep secure)


# Company LinkedIn page
COMPANY_LINKEDIN_URL = "https://www.linkedin.com/company/ini8-labs/"

def get_driver():
    options = ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
    options.add_argument("--ignore-certificate-errors")

    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    # Make selenium less detectable
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    
    return driver

def linkedin_login(driver):
    print("🔐 Logging into LinkedIn...")
    driver.get("https://www.linkedin.com/login")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "username")))

    driver.find_element(By.ID, "username").send_keys(LINKEDIN_EMAIL)
    driver.find_element(By.ID, "password").send_keys(LINKEDIN_PASSWORD)
    driver.find_element(By.ID, "password").send_keys(Keys.RETURN)

    # New: Wait for URL to change or for any visible nav item
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'global-nav')]"))
        )
        print("✅ Logged in successfully.")
    except Exception as e:
        print("❌ Login may have failed.")
        print(driver.current_url)
        with open("error_page.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        raise e

def extract_digits(text):
    match = re.search(r'\d{10,}', text)
    return match.group(0) if match else "N/A"

def get_text_from_about_section(driver, label):
    try:
        elements = driver.find_elements(By.XPATH, "//section[contains(@class, 'artdeco-card') and .//h2[contains(text(), 'About')]]//div[contains(@class, 'org-page-details__definition-term')]")
        for el in elements:
            if label.lower() in el.text.strip().lower():
                value_el = el.find_element(By.XPATH, "./following-sibling::div")
                return value_el.text.strip() if value_el.text.strip() else "N/A"
        return "N/A"
    except:
        return "N/A"

def get_about_details(driver):
    details = {}
    label_list = ["Website", "Phone", "Company size", "Headquarters"]

    for label in label_list:
        try:
            xpath = f"//dt[contains(text(), '{label}')]/following-sibling::dd[1]"
            value = driver.find_element(By.XPATH, xpath).text.strip()
            details[label.lower()] = value
        except:
            try:
                # Try LinkedIn's newer layout using <div>s
                xpath = f"//div[contains(@class,'org-page-details')]//div[contains(text(),'{label}')]/following-sibling::div"
                value = driver.find_element(By.XPATH, xpath).text.strip()
                details[label.lower()] = value
            except:
                details[label.lower()] = "N/A"

    return details

def get_field_text(driver, label):
    try:
        # Check dt/dd format first
        dt_elements = driver.find_elements(By.XPATH, "//dt")
        for dt in dt_elements:
            if dt.text.strip().lower() == label.lower():
                dd = dt.find_element(By.XPATH, "following-sibling::dd[1]")
                return dd.text.strip()
        
        # Fallback: Use div format
        div_elements = driver.find_elements(By.XPATH, f"//div[contains(text(), '{label}')]")
        for div in div_elements:
            try:
                value_div = div.find_element(By.XPATH, "following-sibling::div[1]")
                return value_div.text.strip()
            except:
                continue  # In case no sibling
    except Exception as e:
        pass
    return "N/A"


def scrape_about_details(driver, url):
    print(f"\n🔎 Opening company page: {url}")
    driver.get(url)
    time.sleep(5)

    # Go to About tab
    try:
        about_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(@href,'/about/')]"))
        )
        about_link.click()
    except:
        print("⚠️ About tab not found.")
        return None

    time.sleep(5)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(5)

    try:
        company_name = driver.find_element(By.CLASS_NAME, "org-top-card-summary__title").text.strip()
    except:
        company_name = "N/A"

    website = get_field_text(driver, "Website")
    phone_raw = get_field_text(driver, "Phone")
    phone = extract_digits(phone_raw) if phone_raw != "N/A" else "N/A"
    company_size = get_field_text(driver, "Company size")
    headquarters = get_field_text(driver, "Headquarters")

    return {
        "Company Name": company_name,
        "Website": website,
        "Phone": phone,
        "Company Size": company_size,
        "Headquarters": headquarters,
        "LinkedIn URL": url
    }


def main():
    driver = get_driver()
    linkedin_login(driver)

    data = scrape_about_details(driver, COMPANY_LINKEDIN_URL)

    driver.quit()

    if data:
        df_new = pd.DataFrame([data])
        file_path = "company_linkedin_about.csv"

        try:
            if os.path.exists(file_path):
                df_existing = pd.read_csv(file_path)
                # Drop old entry if same LinkedIn URL already exists
                df_existing = df_existing[df_existing["LinkedIn URL"] != data["LinkedIn URL"]]
                df_combined = pd.concat([df_existing, df_new], ignore_index=True)
            else:
                df_combined = df_new

            df_combined.to_csv(file_path, index=False)
            print(f"\n✅ Company data updated in '{file_path}'")
        except PermissionError:
            print(f"\n⚠️ Cannot write to '{file_path}'. Make sure the file is closed.")


if __name__ == "__main__":
    main()
