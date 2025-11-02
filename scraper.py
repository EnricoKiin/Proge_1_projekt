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
        toote_info_paar = (nimi, link) #Ennik, et hoida info koos
        kasulik_info_kaart.append(toote_info_paar)

    driver.close()
    return kasulik_info_kaart

a = kasulik_info("https://ostukorvid.ee/kategooriad/olu?price=unit")
for el in a:
    toode = a[0]
    toote_link = a[1]
    
    toote_protsent_tekst = re.search(r"(\d+(?:[.,]\d+)?)\s*%", toode)
    toote_protsent = float(toote_protsent_tekst.group(1).replace(',', '.'))
    if toote_protsent == 0.0: #Mõnel alko tootel pandud 0.0, et näidata alkovaba
        continue
    
    toote_maht_tekst = re.search(r"(?:(\d+)\s*[x×*]\s*)?(\d+(?:[.,]\d+)?)\s*(ml|cl|l)", toode)
    if toote_maht_tekst.group(1):
        toodet_pakis = int(toote_maht_tekst.group(1))
    else:
        toodet_pakis = 1
    toote_maht = float(toote_maht_tekst.group(2).replace(',', '.'))
    mahu_ühik = toote_maht_tekst.group(3)
    #konverteerin milliliitriteks
    if mahu_ühik == "ml":
        pass
    elif mahu_ühik == "cl":
        toote_maht *= 10
    else:
        toote_maht *= 1000
    kogu_maht = toodet_pakis * toote_maht #ml
    
    toote_nimi_tekst = re.search(r"^(.*?)\s*\d",toode)
print(protsendid)