""" 
Töö autorid: Enrico Kiin ja Tima Mattias Juksaar
See on scraper ostukorvid.ee lehekülje jaoks, millega saab koguda infot alkohoolitoodete kohta ja selle mõte on leida kõige suurema etanooli sisaldusega toode kõige väiksema hinna eest.
Alguses tee pip install requests beautifulsoup4 playwright terminalis, kuna need pole standard teegid.
"""


import re
import os
import time
import random
import requests


from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from datetime import datetime, timedelta


#Võtsin need siit https://www.zenrows.com/blog/user-agent-web-scraping#best
user_agent_list = ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.2420.81",
"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 OPR/109.0.0.0",
"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
"Mozilla/5.0 (Macintosh; Intel Mac OS X 14.4; rv:124.0) Gecko/20100101 Firefox/124.0",
"Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
"Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 OPR/109.0.0.0",
"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
"Mozilla/5.0 (X11; Linux i686; rv:124.0) Gecko/20100101 Firefox/124.0", ]



def brauser():
    """
    Brauser set-up, millega hakkame lehtedel käima ja scrapima.
    Anname võimalikult palju resursse ja valima contexti suvalisi väärtusi igakord,
    et ei näeks välja nagu sama inimene.
    Keelame piltide ja CSS laadimise, et vähendada aja ja resurssi kulu.
    """
    p = sync_playwright().start()
    storage_state = "auth.json" if os.path.exists("auth.json") else None
    
    browser = p.chromium.launch(
        headless = True,
        args=[
        "--disable-gpu",
        "--disable-extensions",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--blink-settings=imagesEnabled=false",
        "--window-size=1920,1080"
        ]
    )
    
    context = browser.new_context(
        storage_state=storage_state,
        user_agent= random.choice(user_agent_list),
        locale="et-EE",
        timezone_id="Europe/Tallinn",
        viewport={"width": 1920, "height": 1080},
        bypass_csp=True,
    )

    page = context.new_page()
    page.set_default_timeout(15000) #ms
    
    page.route("**/*", lambda route, request:
        route.abort() if request.resource_type in ["image","font","stylesheet"] else route.continue_()
    )

    return p, context, page
    

def uued_küpsised(page, context):
    """
    Loon ja uuendan küpsiseid, et näha rohkem välja nagu inimene mitte bot.
    """
    
    if not os.path.exists("auth.json") or time.time() - os.path.getmtime("auth.json") > 60:
        print("Küpsiste uuendamine")
        page.goto("https://ostukorvid.ee", wait_until="networkidle")
        context.storage_state(path="auth.json")
        print("Valmis")
    else:
        print("Küpsised veel värsekd")


def sitemap_info(sihtmärgid):
    """
    Saan sitemapist vajalikud kategooria leheküljed, millelt tooteid scrapida.
    """
    sitemap_url = "https://ostukorvid.ee/sitemap.xml"
    sitemap_info = requests.get(sitemap_url)
    sitemap_soup = BeautifulSoup(sitemap_info.content, "xml")
    mustad_kategooriad = [loc.text for loc in sitemap_soup.find_all("loc")]
    puhtad_kategooriad = [url for url in mustad_kategooriad if "?tag=" not in url] #Eemaldab alamkategooriad, et vähem asju otsida


    muster = re.compile(rf"/({'|'.join(sihtmärgid)})(?:/|$)", re.IGNORECASE) #Saaks panna ka alguse https://ostukorvid.ee/kategooriad/, aga seega võib ka lihtsamini katki minna
    

    scrape_targets = []
    for leht in puhtad_kategooriad:
        oige = muster.search(leht)
        if oige:
            kategooria = oige.group(1).lower()
            scrape_targets.append((kategooria, leht))
    
    random.shuffle(scrape_targets)
    return scrape_targets


def kasulik_info(page, leht):
    """
    Saan veebilehest kõik kasutatavad tooted, millelt info võtta ja eemaldan kõik pooliku infoga tooted.
    Tagastan järjendi ennikutega, kus igas ennikus on toote nime element ja toote link.
    """
    page.goto(leht)

    page.wait_for_selector(".ml-1.w-full", timeout=10000)
    supp = BeautifulSoup(page.content(), "html.parser")

    info_kaart = supp.select(".ml-1.w-full") #Siin on ka alkoholivabad tooted. Tooted millel pole % märgitud ja tooted millel pole maht märgitud.
    kasulik_info_kaart = []
    for el in info_kaart:
        
        nimi_el = el.select_one(".line-clamp-2.text-base")
        if not nimi_el:
            continue
        nimi_el_tekst = nimi_el.text
        nimi = nimi_el_tekst.strip().lower()
            

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
        
        
        toote_info_paar = (nimi_el_tekst, link)
        kasulik_info_kaart.append(toote_info_paar)
        

    random.shuffle(kasulik_info_kaart)
    return kasulik_info_kaart


def toote_scraper(page, jär, kategooria_nimi):
    """
    Leian kategoorias iga korrektse infoga toote kohta kõik info:
    nimi, maht, protsent, etanooli kogus, etanool euro kohta, poe nimi, hind, millal uuendati.
    Kirjutan kogu selle info vastava kategooria nimega csv faili.
    """

    print(f"Alustan {kategooria_nimi.upper()} scrape'imist.")
    faili_nimi = f"{kategooria_nimi}.csv"
    mitmes_toode = 0
    read = []
    for el in jär:
        toode_el = el[0].strip()
        toode = toode_el.strip().lower()
        toote_link = el[1]
        
        # Leian protsendi
        toote_protsent_match = re.search(r"(\d+(?:[.,]\d+)?)\s*%", toode)
        if not toote_protsent_match:
            print(f"PROTSENT ERROR: {toode}")
            continue

        toote_protsent = float(toote_protsent_match.group(1).replace(',', '.'))
        if toote_protsent == 0.0: #Mõnel alko tootel pandud 0.0, et näidata alkovaba
            print(f"Alkovaba err: {toode}")
            continue
        

        #Leian Mahu
        toote_maht_match = re.search(r"""
                                    (\d+(?:[.,]\d+)?)        #ühiku väärtus nt 500
                                    \s*
                                    (ml|cl|l)(?=\W|$|x|×)""" #ühik
                                    , toode, re.VERBOSE)
        
        if not toote_maht_match:
            print(f"MAHU VIGA: {toode}")
            continue
        

        toote_paki_match = re.search(
                                    r"\b(\d+)\s*(?:x|×|tk|pk|pakk|pakend|karp|kohver)(?=[\s.,]|$)" #Kuna olemas "6tk,"
                                    r"|"
                                    r"(?:^|(?<=[\s.,]))(?:x|×|tk|pk|pakk|pakend|karp|kohver)\s*(\d+)\b",
                                    toode
        )

        if toote_paki_match:
            toodet_pakis = int(toote_paki_match.group(1) or toote_paki_match.group(2))
        else:
            toodet_pakis = 1
        toote_maht = float(toote_maht_match.group(1).replace(',', '.'))
        mahu_ühik = toote_maht_match.group(2)

        #konverteerin milliliitriteks
        if mahu_ühik == "ml":
            pass
        elif mahu_ühik == "cl":
            toote_maht *= 10
        else:
            toote_maht *= 1000
        kogu_maht = toodet_pakis * toote_maht #ml


        #Leian nime
        toote_nimi = toode_el
        
        
        # Vastava poe või poodide info leidmine
        try:
            page.goto(toote_link)
            time.sleep(random.uniform(0.8, 2.2))
            page.wait_for_selector(".col-span-2.mt-2", timeout=5000)
        except:
            print(f"Poeinfot ei ilmunud: {toote_link}")
            continue
            
        info_supp = BeautifulSoup(page.content(), "html.parser")
        sega_info = info_supp.select_one(".col-span-2.mt-2")

        if not sega_info:
            print(f"Ei leidnud poe infot lehel: {toote_link}")
            continue
          
        poed = sega_info.find_all("a")

        for pood in poed:
     
            #Leian poe nime
            poe_nimi = None
            for span in pood.find_all("span"):
                tekst = span.get_text(strip=True)
                if tekst:
                    poe_nimi = tekst
                    break
                    
                    
            #Leian hinna
            hind_el = pood.select_one("span.text-xl.font-bold")
            if hind_el:
                hind_tekst = hind_el.text.strip()
                hind = float(re.search(r"(\d+(?:[.,]\d+)?)\s*€", hind_tekst).group(1).replace(',', '.'))
            else:
                hind = None


            #Leian millal viimati uuendati 
            ühikud = {
                "sekund": 1, "sekundit": 1,
                "minut": 60, "minutit": 60,
                "tund": 3600, "tundi": 3600,
                "päev": 86400, "päeva": 86400,
                "nädal": 604800, "nädalat": 604800,
                "kuu": 2592000, "kuud": 2592000,
                "aasta": 31536000, "aastat": 31536000
                }
            viimati_uuendatud_el = pood.select_one("span.mr-1.hidden.text-xs.text-gray-600")
            aeg_ümar = None
            if viimati_uuendatud_el:
                viimati_uuendatud_sisu = viimati_uuendatud_el.text.strip().lower()
                viimati_uuendatud_tekst = re.search(r"""(?:(\d+)[\s\u00A0\u202F]*)? #väärtus
                                                    ([\wäöüõ]+)                     #ühik
                                                    (?:[\s\u00A0\u202F]+aega)?      #\u00A0 - nbsp \u202F - nbsp narrrow. Siin vaja millegipärast, muidu annab None vahest
                                                    [\s\u00A0\u202F]*tagasi""",
                                                    viimati_uuendatud_sisu, flags=re.UNICODE | re.VERBOSE)
                if viimati_uuendatud_tekst:
                    aja_väärtus = int(viimati_uuendatud_tekst.group(1)) if viimati_uuendatud_tekst.group(1) else 1 #Kuna tekstis on "uuendatud: tund/minut/päev aega tagasi"
                    ühiku_väärtus = viimati_uuendatud_tekst.group(2)
                    sekundi_väärtus = ühikud.get(ühiku_väärtus)
                    if not sekundi_väärtus:
                        aeg_ümar = "None_sekundi_väärtus"
                    else:
                        aja_erinevus = timedelta(seconds= sekundi_väärtus * aja_väärtus)
                        aeg = datetime.now() - aja_erinevus
                        aeg_ümar = aeg.replace(second=0, microsecond=0)
            
            
            etanool = round(kogu_maht * (toote_protsent / 100), 3)
            etanool_euro_kohta = round(kogu_maht * (toote_protsent / 100) / hind, 3)
            

            read.append([toote_nimi,
                        kogu_maht,
                        toote_protsent,
                        etanool,
                        etanool_euro_kohta,
                        poe_nimi,
                        hind,
                        aeg_ümar,
                        toote_link
                        ])
            

            mitmes_toode += 1
            print(f"{mitmes_toode}", end="\r")
    
    #Sorteerin read kõige suurema etanool_euro_kohta järgi
    read.sort(key=lambda väärtus: väärtus[4], reverse=True)
    with open(faili_nimi, "w", encoding="UTF-8") as f:
        f.write("Toode;Maht_ml;Protsent;Etanool;Etanool/€;Pood;Hind;Uuendatud;Link\n")
        for rida in read:
            f.write(";".join(str(el) for el in rida) + "\n")
    
    print(f"{kategooria_nimi.upper()} on scrapeitud.")
    print(f"Unikaalseid tooteid oli: {len(jär)}")
    print(f"Sissekandeid oli: {len(read)}")
    for i in range(2):
        print()


def main():
    """
    Scrapin ostukorvid.ee lehte, et leida igas soovitud kategooria kõige odavama toote, mis sisaldab kõige rohkem etanooli.
    Tagastan info csv failidena.
    """
    p, context, page = brauser()
    uued_küpsised(page, context)
    
    scrapeime = ["olu", "viin", "siider", "vein"]
    kategooriad = sitemap_info(scrapeime)

    for i, (kategooria_nimi, leht) in enumerate(kategooriad):
        if i % 2 == 0:
            uued_küpsised(page, context)
        tooted = kasulik_info(page, leht)
        toote_scraper(page, tooted, kategooria_nimi)
    
    context.close()
    p.stop()

if __name__=="__main__":
    main()
