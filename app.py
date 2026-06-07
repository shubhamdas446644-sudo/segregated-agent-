import streamlit as st
import asyncio
from playwright.async_api import async_playwright
import pandas as pd
import io

# Playwright Scraper Function (Headless for cloud)
async def extract_maps_data(search_keyword, max_results):
    async with async_playwright() as p:
        # Cloud par headless=True rakhna zaroori hai
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        formatted_query = search_keyword.replace(" ", "+")
        await page.goto(f"https://www.google.com/maps/search/{formatted_query}", timeout=60000)
        await asyncio.sleep(5)

        panel_selector = 'div[role="feed"]'
        # Auto-scroll loops based on requested results
        scroll_loops = 30 if max_results > 50 else 15
        for _ in range(scroll_loops):
            try:
                await page.evaluate(f"document.querySelector('{panel_selector}').scrollTo(0, document.querySelector('{panel_selector}').scrollHeight)")
                await asyncio.sleep(1.5)
            except:
                break

        links = await page.locator('a[href*="/maps/place/"]').all()
        urls = [await link.get_attribute('href') for link in links]
        urls = list(set(urls))[:max_results]
        
        leads = []
        for idx, url in enumerate(urls, 1):
            try:
                await page.goto(url, timeout=60000)
                await asyncio.sleep(2)

                name = await page.locator('h1.DUwDvf').text_content() if await page.locator('h1.DUwDvf').count() > 0 else "N/A"
                rating = await page.locator('div.F7nice span span').first.text_content() if await page.locator('div.F7nice span span').count() > 0 else "No Rating"
                reviews = await page.locator('div.F7nice span span').last.text_content() if await page.locator('div.F7nice span span').count() > 1 else "0"
                
                address, phone, website = "N/A", "N/A", "N/A"
                buttons = await page.locator('button[data-item-id]').all()
                for btn in buttons:
                    item_id = await btn.get_attribute('data-item-id')
                    if item_id and "address" in item_id: address = await btn.text_content()
                    elif item_id and "phone:tel:" in item_id: phone = await btn.text_content()
                    elif item_id and "authority" in item_id: website = await btn.text_content()

                leads.append({
                    "Shop Name": name.strip(),
                    "Rating": rating.strip(),
                    "Total Reviews": reviews.replace('(','').replace(')','').strip(),
                    "Phone Number": phone.strip(),
                    "Website": website.strip(),
                    "Address": address.strip(),
                    "Maps Link": url
                })
            except:
                continue

        await browser.close()
        return leads

# --- STREAMLIT UI (Website Design) ---
st.set_page_config(page_title="Namvio Lead Extractor", page_icon="🎯")
st.title("🚀 Namvio Google Maps Lead Extractor")
st.write("Ab aap mobile se hi bina laptop ke leads nikal sakte hain!")

# Inputs
keyword = st.text_input("Enter Search Keyword:", placeholder="e.g., Dental Clinic in Mumbai")
limit = st.slider("Max Results:", min_value=5, max_value=100, value=20)

if st.button("Start Scraping 🤖"):
    if not keyword:
        st.warning("Please enter a keyword first!")
    else:
        with st.spinner("Agent maps par live scroll kar raha hai... Please wait 5-10 mins..."):
            # Run async function in streamlit
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            results = loop.run_until_complete(extract_maps_data(keyword, limit))
            
            if results:
                df = pd.DataFrame(results)
                st.success(f"🎉 Successfully Extracted {len(df)} Unique Leads!")
                
                # Create Excel in memory for download button
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                
                # Download Button
                st.download_button(
                    label="📥 Download Excel File",
                    data=buffer.getvalue(),
                    file_name=f"leads_{keyword.replace(' ','_')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.error("📭 No data found. Try another keyword.")