import streamlit as st
import pandas as pd
import os
from scraper import get_driver, linkedin_login, scrape_about_details  # Replace with your actual filename

st.set_page_config(page_title="LinkedIn Company Scraper", layout="centered")

st.title("🔍 LinkedIn Company Scraper")

# Step 1: Ask for company name only
company_name = st.text_input("Enter Company Name (as in LinkedIn URL)", "hcltech")

# Step 2: Auto-generate LinkedIn URL
linkedin_url = f"https://www.linkedin.com/company/{company_name.strip().lower()}/"
st.markdown(f"🔗 LinkedIn URL to be scraped: [{linkedin_url}]({linkedin_url})")

if st.button("Scrape Company Info"):
    with st.spinner("Scraping LinkedIn company data..."):
        try:
            driver = get_driver()
            linkedin_login(driver)
            data = scrape_about_details(driver, linkedin_url)
            driver.quit()

            if data:
                df = pd.DataFrame([data])
                st.success("✅ Data scraped successfully!")
                st.dataframe(df)

                file_path = "company_linkedin_about.csv"
                if os.path.exists(file_path):
                    df_existing = pd.read_csv(file_path)
                    df_existing = df_existing[df_existing["LinkedIn URL"] != data["LinkedIn URL"]]
                    df_combined = pd.concat([df_existing, df], ignore_index=True)
                else:
                    df_combined = df

                df_combined.to_csv(file_path, index=False)
                st.download_button("📥 Download CSV", df_combined.to_csv(index=False), file_name="company_data.csv")

            else:
                st.error("❌ Failed to scrape the company details.")
        except Exception as e:
            st.error(f"An error occurred: {e}")
