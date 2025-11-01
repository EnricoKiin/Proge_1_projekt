#Alguses tee pip install requests beautifulsoup4 selenium terminalis. Muidu ei tööta

# class=ml-1.w-full selles on kogu info
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import re

# Seleniumi seadistamine, et brauser ei sulguks automaatselt
options = Options()
options.add_experimental_option("detach", True)
driver = webdriver.Chrome(options=options)
driver.get("https://ostukorvid.ee/kategooriad/olu?price=unit") # Ava veebileht

# Kasutame BeautifulSoupi, et saada sitemapist kategooriad ning seejärel leiame nende kategooriate veebilehed, mida soovime
sitemap_url = "https://ostukorvid.ee/sitemap.xml"
sitemap_info = requests.get(sitemap_url)
sitemap_soup = BeautifulSoup(sitemap_info.content, "xml")
mustad_kategooriad = [loc.text for loc in sitemap_soup.find_all("loc")]
puhtad_kategooriad = [url for url in mustad_kategooriad if "?tag=" not in url] #Eemaldab alamkategooriad, et vähem asju otsida

scrape_info = ["olu", "viin", "siider", "vein"]
scrape_targets = []
for url in puhtad_kategooriad:
    for el in scrape_info:
        if re.search(rf"/{el}\b", url, re.IGNORECASE): # \b - boundary - leiab ainult need võtmasõnad, mida tahame
            scrape_targets.append(url)
            break
