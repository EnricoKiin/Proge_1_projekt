# pip install playwright beautifulsoup4 requests
# python -m playwright install chromium

import asyncio
import re
import time
import random
import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


# --- Helper: safer page.goto with retries ---
async def safe_goto(page, url, retries=2, delay_range=(0.3, 1.0)):
    for attempt in range(1, retries + 1):
        try:
            await page.goto(url, wait_until="networkidle", timeout=25000)
            title = await page.title()
            if "404" in title.lower():
                print(f"❌ 404 not found: {url}")
                return False
            return True
        except Exception as e:
            print(f"⚠️ Timeout ({attempt}/{retries}) at {url}")
            await asyncio.sleep(random.uniform(*delay_range))
    return False


# --- Scrape category page to get product links ---
async def kasulik_info(page, leht):
    if not await safe_goto(page, leht):
        print(f"❌ Ei saanud avada kategooriat: {leht}")
        return []

    try:
        await page.wait_for_selector(".ml-1.w-full", timeout=15000)
    except:
        print(f"⚠️ Tooteid ei leitud: {leht}")
        return []

    html = await page.content()
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select(".ml-1.w-full")

    results = []
    for el in cards:
        nimi_el = el.select_one(".line-clamp-2.text-base")
        if not nimi_el:
            continue

        nimi = nimi_el.text.strip().lower()
        if "%" not in nimi:
            continue
        if not any(x in nimi for x in ["ml", "cl", "l"]):
            continue
        if "alk.vaba" in nimi or "alkoholivaba" in nimi:
            continue

        a_tag = nimi_el.find_parent("a")
        if not a_tag or not a_tag.get("href"):
            continue
        link = a_tag["href"]
        if not link.startswith("http"):
            link = "https://ostukorvid.ee" + link

        results.append((nimi, link))
    return results


# --- Scrape a single product page ---
async def scrape_product(context, product):
    toode, toote_link = product
    page = await context.new_page()

    # block unnecessary resources
    await page.route("**/*", lambda route, request: asyncio.create_task(
        route.abort()) if request.resource_type in ["image", "stylesheet", "font"]
        else asyncio.create_task(route.continue_()))

    try:
        if not await safe_goto(page, toote_link):
            await page.close()
            return None

        await page.wait_for_selector(".col-span-2.mt-2", timeout=10000)
        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")
        sega_info = soup.select_one(".col-span-2.mt-2")
        if not sega_info:
            await page.close()
            return None

        # protsent
        protsent_match = re.search(r"(\d+(?:[.,]\d+)?)\s*%", toode)
        if not protsent_match:
            await page.close()
            return None
        protsent = float(protsent_match.group(1).replace(",", "."))

        # maht
        maht_match = re.search(
            r"(?:(\d+)\s*[x×*]\s*)?(\d+(?:[.,]\d+)?)\s*(ml|cl|l)", toode, re.VERBOSE)
        if not maht_match:
            await page.close()
            return None

        kogus = int(maht_match.group(1)) if maht_match.group(1) else 1
        maht = float(maht_match.group(2).replace(",", "."))
        unit = maht_match.group(3)
        if unit == "cl":
            maht *= 10
        elif unit == "l":
            maht *= 1000
        kogu_maht = kogus * maht

        name_match = re.search(r"^(.*?)\s*\d", toode)
        nimi = name_match.group(1).strip() if name_match else toode
        result = [nimi, kogu_maht, protsent]

        # poe info
        for pood in sega_info.find_all("a"):
            poe_nimi = None
            for span in pood.find_all("span"):
                text = span.get_text(strip=True)
                if text:
                    poe_nimi = text
                    break
            hind_el = pood.select_one("span.text-xl.font-bold")
            if hind_el:
                hind_tekst = hind_el.text.strip()
                hind = float(
                    re.search(r"(\d+(?:[.,]\d+)?)\s*€", hind_tekst).group(1).replace(",", ".")
                )
            else:
                hind = None
            result.append((poe_nimi, hind))

        await asyncio.sleep(random.uniform(0.2, 0.5))  # polite delay
        return result

    except Exception as e:
        print(f"⚠️ Error on {toote_link}: {type(e).__name__}")
    finally:
        await page.close()
    return None


# --- MAIN ---
async def main():
    sitemap_url = "https://ostukorvid.ee/sitemap.xml"
    sitemap_info = requests.get(sitemap_url)
    sitemap_soup = BeautifulSoup(sitemap_info.content, "xml")
    mustad_kategooriad = [loc.text for loc in sitemap_soup.find_all("loc")]
    puhtad_kategooriad = [url for url in mustad_kategooriad if "?tag=" not in url]

    scrape_info = ["olu", "viin", "siider", "vein"]
    muster = re.compile(rf"/({'|'.join(scrape_info)})(?:/|$)", re.IGNORECASE)
    scrape_targets = [url for url in puhtad_kategooriad if muster.search(url)]

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-gpu",
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        )

        page = await context.new_page()
        products = await kasulik_info(page, "https://ostukorvid.ee/kategooriad/olu?price=unit")
        await page.close()

        print(f"Leitud {len(products)} toodet.\n")

        start = time.time()
        sem = asyncio.Semaphore(3)  # limit concurrency to 3 at once

        async def sem_task(prod):
            async with sem:
                await asyncio.sleep(random.uniform(0.1, 0.6))
                return await scrape_product(context, prod)

        tasks = [asyncio.create_task(sem_task(prod)) for prod in products]
        results = []
        for i, t in enumerate(asyncio.as_completed(tasks), 1):
            res = await t
            if res:
                results.append(res)
            print(f"{i}/{len(products)} toodet töödeldud ✓")

        await browser.close()
        print(f"\nKokku {len(results)} toodet — {round(time.time() - start, 2)} sekundit")


if __name__ == "__main__":
    asyncio.run(main())
