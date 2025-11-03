# pip install requests beautifulsoup4 selenium
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import time
import random


# --- 🧠 Chrome setup (lightweight) ---
def make_driver():
    options = Options()
    options.add_argument("--headless=chrome")  # modern headless mode
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-client-side-phishing-detection")
    options.add_argument("--disable-sync")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--single-process")
    options.add_argument("--disable-features=VizDisplayCompositor")
    options.add_argument("--blink-settings=imagesEnabled=false")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disk-cache-size=0")

    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.managed_default_content_settings.fonts": 2,
        "profile.managed_default_content_settings.stylesheets": 2,
        "profile.managed_default_content_settings.cookies": 2,
    }
    options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(60)
    return driver


# --- 🧩 Load all valid products from category page ---
def kasulik_info(driver, leht):
    for attempt in range(2):
        try:
            print(f"🌐 Loading category: {leht} (attempt {attempt+1})")
            driver.get(leht)

            WebDriverWait(driver, 20).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            time.sleep(2)  # React hydration wait
            break
        except Exception as e:
            print(f"⚠️ Category load error ({type(e).__name__}) — retrying...")
            if attempt == 1:
                raise

    supp = BeautifulSoup(driver.page_source, "html.parser")
    info_kaart = supp.select(".ml-1.w-full")

    kasulik_info_kaart = []
    for el in info_kaart:
        nimi_el = el.select_one(".line-clamp-2.text-base")
        if not nimi_el:
            continue
        nimi = nimi_el.text.strip().lower()

        if "%" not in nimi:
            continue
        elif not any(x in nimi for x in ["ml", "cl", "l"]):
            continue
        elif "alk.vaba" in nimi or "alkoholivaba" in nimi:
            continue

        parent_el = nimi_el.find_parent("a")
        if not parent_el or not parent_el.has_attr("href"):
            continue

        link = parent_el["href"]
        if not link.startswith("http"):
            link = "https://ostukorvid.ee" + link
        kasulik_info_kaart.append((nimi, link))

    return kasulik_info_kaart


# --- 🧩 Scrape single product (2 retries) ---
def scrape_product(el):
    driver = make_driver()
    toode, toote_link = el
    result = None

    for attempt in range(2):
        try:
            protsent_match = re.search(r"(\d+(?:[.,]\d+)?)\s*%", toode)
            if not protsent_match:
                return None
            protsent = float(protsent_match.group(1).replace(",", "."))

            maht_match = re.search(
                r"(?:(\d+)\s*[x×*]\s*)?(\d+(?:[.,]\d+)?)\s*(ml|cl|l)", toode, re.VERBOSE
            )
            if not maht_match:
                return None

            pakis = int(maht_match.group(1)) if maht_match.group(1) else 1
            maht = float(maht_match.group(2).replace(",", "."))
            ühik = maht_match.group(3)
            if ühik == "cl":
                maht *= 10
            elif ühik == "l":
                maht *= 1000
            kogu_maht = pakis * maht

            nimi_match = re.search(r"^(.*?)\s*\d", toode)
            nimi = nimi_match.group(1).strip() if nimi_match else toode

            driver.get(toote_link)
            WebDriverWait(driver, 20).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            time.sleep(1.0)

            supp = BeautifulSoup(driver.page_source, "html.parser")
            sega_info = supp.select_one(".col-span-2.mt-2")
            if not sega_info:
                raise Exception("Store info not found")

            poed = sega_info.find_all("a")
            poeandmed = []
            for pood in poed:
                poe_nimi = None
                for span in pood.find_all("span"):
                    tekst = span.get_text(strip=True)
                    if tekst:
                        poe_nimi = tekst
                        break

                hind_el = pood.select_one("span.text-xl.font-bold")
                hind = (
                    float(
                        re.search(r"(\d+(?:[.,]\d+)?)\s*€", hind_el.text)
                        .group(1)
                        .replace(",", ".")
                    )
                    if hind_el
                    else None
                )
                if poe_nimi:
                    poeandmed.append((poe_nimi, hind))

            result = [nimi, kogu_maht, protsent] + poeandmed
            break

        except Exception as e:
            print(f"⚠️ {type(e).__name__} on attempt {attempt+1} for {toote_link}")
            if attempt == 0:
                time.sleep(2)
                driver.refresh()
            else:
                result = None

    driver.quit()
    return result


# --- 🧩 Main ---
if __name__ == "__main__":
    start_time = time.time()
    driver_main = make_driver()
    category_url = "https://ostukorvid.ee/kategooriad/olu?price=unit"

    print(f"\n📦 Laen toodete nimekirja: {category_url}")
    try:
        products = kasulik_info(driver_main, category_url)
    finally:
        driver_main.quit()

    print(f"✅ {len(products)} toodet leitud.\n")

    lõpp_tulemus = []
    random.shuffle(products)  # avoids same-store blocking

    # --- 2-driver parallel scraping ---
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(scrape_product, el) for el in products]
        for i, f in enumerate(as_completed(futures), 1):
            result = f.result()
            if result:
                lõpp_tulemus.append(result)
            print(f"{i}/{len(products)} toodet töödeldud ✓")

    print(f"\n✅ Valmis! {len(lõpp_tulemus)} toodet edukalt salvestatud.")
    print(f"⏱️ Koguaeg: {time.time() - start_time:.1f} sekundit")
