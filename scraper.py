#Alguses tee pip install requests beautifulsoup4 selenium terminalis. Muidu ei tööta

# class=ml-1.w-full selles on kogu info
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re

# Seleniumi seadistamine, et brauser ei sulguks automaatselt
options = Options()
options.add_experimental_option("detach", True)
driver = webdriver.Chrome(options=options)

# Kasutame BeautifulSoupi, et saada sitemapist kategooriad ning seejärel leiame nende kategooriate veebilehed, mida soovime
sitemap_url = "https://ostukorvid.ee/sitemap.xml"
sitemap_info = requests.get(sitemap_url)
sitemap_soup = BeautifulSoup(sitemap_info.content, "xml")
mustad_kategooriad = [loc.text for loc in sitemap_soup.find_all("loc")]
puhtad_kategooriad = [url for url in mustad_kategooriad if "?tag=" not in url] #Eemaldab alamkategooriad, et vähem asju otsida

scrape_info = ["olu", "viin", "siider", "vein"]

muster = re.compile(rf"/({'|'.join(scrape_info)})(?:/|$)", re.IGNORECASE) #Saaks panna ka alguse https://ostukorvid.ee/kategooriad/, aga seega võib ka lihtsamini katki minna

scrape_targets = [url for url in puhtad_kategooriad if muster.search(url)]

#Saan veebilehest kõik kasutatavad tooted, millelt info võtta ja eemaldan kõik pooliku infoga tooted
def kasulik_info(leht):
    driver.get(leht)

    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".ml-1.w-full")))

    supp = BeautifulSoup(driver.page_source, "html.parser")

    info_kaart = [el for el in supp.select(".ml-1.w-full")] #Siin on ka alkoholivabad tooted. Tooted millel pole % märgitud ja tooted millel pole maht märgitud.
    kasulik_info_kaart = []
    #print(info_kaart)
    nimed = []
    for el in info_kaart:
        nimi = el.select_one(".line-clamp-2.text-base").text.strip().lower()
        if "%" and "vol" not in nimi:
            continue
        elif "ml" and "cl" and "l" not in nimi:
            continue
        elif "alk.vaba" in nimi or "alkoholivaba" in nimi:
            continue
        else:
            kasulik_info_kaart.append(el)
    driver.close
    return kasulik_info_kaart

"""def toote_info_kaartidest(jär):
    for el in jär:
        rida = el.select_one(".line-clamp-2.text-base").text.strip().lower()
        toote_protsent =
        toote_maht = re.search()"""
"""protsendid = []
a = kasulik_info("https://ostukorvid.ee/kategooriad/olu?price=unit")
for el in a:
    toode = el.select_one(".line-clamp-2.text-base").text.strip().lower()
    pr_i = toode.index("%")
    protsent = toode[(pr_i - 5):(pr_i + 4)]
    protsendid.append(protsent)
print(protsendid)"""