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
from Context_lists import user_agent_list, locale_timezone_list


def brauser():
    """
    Brauser set-up, millega hakkame lehtedel käima ja scrapima.
    Anname võimalikult palju resursse ja valima contexti suvalisi väärtusi igakord,
    et ei näeks välja nagu sama inimene.
    Keelame piltide ja CSS laadimise, et vähendada aja ja resurssi kulu.
    """
    p = sync_playwright().start()
    storage_state = "auth.json" if os.path.exists("auth.json") else None
    suvaline_locale_timzone_dict = random.choice(locale_timezone_list)

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
        locale=suvaline_locale_timzone_dict["locale"],
        timezone_id=suvaline_locale_timzone_dict["timezone"],
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
    
    print("Küpsiste uuendamine")
    page.goto("https://ostukorvid.ee", wait_until="networkidle")
    context.storage_state(path="auth.json")
    print("Valmis")


def värskenda_context_küpsised(p, vana_context):
    """
    Contexti värskendamiseks, et vähendada lehe throttle võimalusi.
    """

    vana_context.close()
    browser = vana_context.browser
    storage_state = "auth.json" if os.path.exists("auth.json") else None
    suvaline_locale_timzone_dict = random.choice(locale_timezone_list)
    
    context = browser.new_context(
        storage_state=storage_state,
        user_agent= random.choice(user_agent_list),
        locale=suvaline_locale_timzone_dict["locale"],
        timezone_id=suvaline_locale_timzone_dict["timezone"],
        viewport={"width": 1920, "height": 1080},
        bypass_csp=True,
    )

    page = context.new_page()
    page.set_default_timeout(15000) #ms
    
    page.route("**/*", lambda route, request:
        route.abort() if request.resource_type in ["image","font","stylesheet"] else route.continue_()
    )
    
    uued_küpsised(page, context)

    return context, page


def safe_goto(page, leht, proove=3, timeout=15000):
    """
    Abifunktsioon, et saaks mitu korda ühte linki proovida,
    kui esimesel korral tuleb TimeOutError. Ainult toote_scraper() jaoks.
    """
    for katse in range(proove):
        try:
            page.goto(leht, wait_until="networkidle", timeout=timeout)
            if page.locator(".col-span-2.mt-2").count() > 0:
                return True
            page.wait_for_selector(".col-span-2.mt-2", timeout=timeout)
            return True
        except:
            print(f"Proovin uuesti lehte {leht}. Nüüd on proov nr {katse + 1}")
            time.sleep(random.uniform(2.0, 5.0))
    print(f"Poe infot ei ilmunud pärast {proove} katset. Toode: {leht}")
    return False


def sitemap_info(sihtmärgid):
    """
    Saan sitemapist vajalikud kategooria leheküljed, millelt tooteid scrapida.
    """
    sitemap_url = "https://ostukorvid.ee/sitemap.xml"
    sitemap_info = requests.get(sitemap_url)
    sitemap_soup = BeautifulSoup(sitemap_info.content, "xml")
    mustad_kategooriad = [loc.text for loc in sitemap_soup.find_all("loc")]
    puhtad_kategooriad = [url for url in mustad_kategooriad if "?tag=" not in url] #Eemaldab alamkategooriad, et vähem asju otsida


    muster = re.compile(rf"/({'|'.join(sihtmärgid)})(?:/|$)", re.IGNORECASE) 
    

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
    Tagastan järjendi ennikutega, kus igas ennikus on toote nime element, toote mahtu tekst ja toote link.
    """
    page.goto(leht)

    page.wait_for_selector("a.m-1.inline-flex.items-center.rounded.border-2.border-gray-300.p-1", timeout=25000)
    supp = BeautifulSoup(page.content(), "html.parser")

    info_kaardid = supp.select("a.m-1.inline-flex.items-center.rounded.border-2.border-gray-300.p-1") #Siin on ka alkoholivabad tooted ja Tooted millel pole % märgitud.
    
    kasulikud_info_kaardid = []

    for el in info_kaardid:
        nimi_el = el.select_one(".line-clamp-2.text-base")
        if not nimi_el:
            continue

        nimi_el_tekst = nimi_el.text.strip()
        nimi = nimi_el_tekst.lower()

        if "%" not in nimi:
            continue
        elif "alk.vaba" in nimi or "alkoholivaba" in nimi:
            continue

        maht_el = el.select_one("div.relative span")
        
        if not maht_el:
            continue
        maht = maht_el.text.strip().lower()
        
        if not any(x in maht for x in ["ml", "cl", "l"]):
            continue
        

        link = el.get("href", "")
        if not link:
            continue
        if not link.startswith("http"):
            link = "https://ostukorvid.ee" + link
        
        
        toote_info_paar = (nimi_el_tekst, maht, link)
        kasulikud_info_kaardid.append(toote_info_paar)
        

    random.shuffle(kasulikud_info_kaardid)
    return kasulikud_info_kaardid


def toote_scraper(p, page, jär, kategooria_nimi):
    """
    Leian kategoorias iga korrektse infoga toote kohta kõik info:
    nimi, maht, protsent, etanooli kogus, etanool euro kohta, poe nimi, hind, millal uuendati.
    Kirjutan kogu selle info vastava kategooria nimega csv faili.
    """

    print(f"Alustan {kategooria_nimi.upper()} scrape'imist.")
    faili_nimi = f"{kategooria_nimi}.csv"
    mitmes_toode = 0
    read = []
    
    toote_protsent_muster = re.compile(r"(\d+(?:[.,]\d+)?)\s*%", re.IGNORECASE)
    
    toote_maht_muster = re.compile(r"""
                                    (\d+(?:[.,]\d+)?)  # ühiku väärtus nt 500
                                    \s*
                                    (ml|cl|l)          # ühik
                                    """ 
                                    , re.VERBOSE | re.IGNORECASE)
    
    
    hind_muster = re.compile(r"(\d+(?:[.,]\d+)?)\s*€", re.IGNORECASE)
    
    viimati_uuendatud_muster = re.compile(r"""(?:(\d+)[\s\u00A0\u202F]*)?           #väärtus
                                                    ([\wäöüõ]+)                     #ühik
                                                    (?:[\s\u00A0\u202F]+aega)?      #\u00A0 - nbsp \u202F - nbsp narrrow. Siin vaja millegipärast, muidu annab None vahest
                                                    [\s\u00A0\u202F]*tagasi""",
                                                    re.UNICODE | re.VERBOSE | re.IGNORECASE)
    for el in jär:
        if mitmes_toode % 20 == 0:
            time.sleep(random.uniform(3.0, 6.0))
        if mitmes_toode != 0 and mitmes_toode % 100 == 0:
            context, page = värskenda_context_küpsised(p, page.context)
            print("Scraper värskendatud")
        

        toode_el = el[0].strip()
        toode = toode_el.strip().lower()
        toote_maht_tekst = el[1]
        toote_link = el[2]
        
        # Leian protsendi
        protsent_tekst = toote_protsent_muster.search(toode)
        if not protsent_tekst:
            print(f"PROTSENT ERROR: {toode}")
            continue

        toote_protsent = float(protsent_tekst.group(1).replace(',', '.'))
        if toote_protsent == 0.0: #Mõnel alko tootel pandud 0.0, et näidata alkovaba
            print(f"Alkovaba err: {toode}")
            continue
        

        #Leian Mahu
        
        maht_tekst = toote_maht_muster.search(toote_maht_tekst)
        if not maht_tekst:
            print(f"MAHU VIGA: {toode}")
            continue
        toote_maht = float(maht_tekst.group(1).replace(',', '.'))
        
        mahu_ühik = maht_tekst.group(2)

        #konverteerin milliliitriteks
        if mahu_ühik == "ml":
            pass
        elif mahu_ühik == "cl":
            toote_maht *= 10
        else:
            toote_maht *= 1000


        #Leian nime
        toote_nimi = toode_el
        
        
        # Vastava poe või poodide info leidmine
        time.sleep(random.uniform(0.8, 2.2))
        if not safe_goto(page, toote_link):
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
                hind = float(hind_muster.search(hind_tekst).group(1).replace(',', '.'))
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
                viimati_uuendatud_tekst = viimati_uuendatud_muster.search(viimati_uuendatud_sisu)
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
            
            
            etanool = round(toote_maht * (toote_protsent / 100), 3)
            etanool_euro_kohta = round(toote_maht * (toote_protsent / 100) / hind, 3)
            

            read.append([toote_nimi,
                        toote_maht,
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

    return page.context, page


def main():
    """
    Scrapin ostukorvid.ee lehte, et leida igas soovitud kategooria kõige odavama toote, mis sisaldab kõige rohkem etanooli.
    Tagastan info csv failidena.
    """
    p, context, page = brauser()
    uued_küpsised(page, context)
    
    scrapeime = ["olu", "viin", "siider", "vein"]
    kategooriad = sitemap_info(scrapeime)

    for kategooria_nimi, leht in kategooriad:
        tooted = kasulik_info(page, leht)
        context, page = toote_scraper(p, page, tooted, kategooria_nimi)
    
    context.close()
    p.stop()

if __name__=="__main__":
    main()
