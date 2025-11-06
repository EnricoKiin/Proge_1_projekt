#Alguses tee pip install requests beautifulsoup4 selenium terminalis. Muidu ei tööta

# class=ml-1.w-full selles on kogu info
from playwright.sync_api import sync_playwright
import requests, re, time, random, os
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
"Mozilla/5.0 (X11; Linux i686; rv:124.0) Gecko/20100101 Firefox/124.0"]
# Playwright seadistus
with sync_playwright() as p:
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
    #Natuke lisainfot igale browserile, et me ei näeks liiga scraperi moodi välja

    context = browser.new_context(
        storage_state=storage_state,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        locale="et-EE",
        timezone_id="Europe/Tallinn",
        viewport={"width": 1920, "height": 1080},
        bypass_csp=True,
    )
    page = context.new_page()
    page.set_default_timeout(15000)
    page.route("**/*", lambda route, request:
        route.abort() if request.resource_type in ["image","font","stylesheet"] else route.continue_()
    )
    
    if time.time() - os.path.getmtime("auth.json") > 60:
        print("Küpsiste uuendamine")
        page.goto("https://ostukorvid.ee", wait_until="networkidle")
        context.storage_state(path="auth.json")
        print("Valmis")
    else:
        print("Küpsised veel värsekd")



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
            toote_info_paar = (nimi_el_tekst, link) #Ennik, et hoida info koos
            kasulik_info_kaart.append(toote_info_paar)
        return kasulik_info_kaart
    """
    lõpp_tulemus = []
    mahu_err = 0
    prot_err = 0
    prot_err_alk_vaba = 0
    mitmes_tood = 0
    print(lõpp_tulemus)
    print(mahu_err)
    print(prot_err)
    print(prot_err_alk_vaba)
    """
    mitmes_tood = 0
    a = kasulik_info("https://ostukorvid.ee/kategooriad/olu?price=unit")
    random.shuffle(a)
    print(len(a))
    with open("olu_tulemus.csv", "w", encoding="UTF-8") as f:
        f.write("Toode;Maht_ml;Protsent;Pood;Hind;Uuendatud;Link\n")
        for el in a:
            toode_el = el[0].strip()
            toode = toode_el.strip().lower()
            toote_link = el[1]
            
            # Leian protsendi
            toote_protsent_match = re.search(r"(\d+(?:[.,]\d+)?)\s*%", toode)
            if not toote_protsent_match:
                #prot_err += 1
                continue

            toote_protsent = float(toote_protsent_match.group(1).replace(',', '.'))
            if toote_protsent == 0.0: #Mõnel alko tootel pandud 0.0, et näidata alkovaba
                print(f"Alkovaba err: {toode}")
                #prot_err_alk_vaba += 1
                continue
            



            #Leian Mahu
            toote_maht_match = re.search(r"""
                                        (\d+(?:[.,]\d+)?) #ühiku väärtus nt 500
                                        \s*
                                        (ml|cl|l)\b""" #ühik
                                        , toode, re.VERBOSE)
            toote_paki_match = (
             re.search(r"(\d+)\s*(?:x|×|[-]?\s*(?:pakk|pakend|pk|tk|karp|kohver))", toode, re.IGNORECASE)
             or
             re.search(r"(?:x|×)\s*(\d+)\s*(?:tk|pk|pakk|pakend|karp|kohver)?", toode, re.IGNORECASE))
            if not toote_maht_match:
                print(f"MAHU VIGA: {toode}")
                #mahu_err += 1
                continue

            if toote_paki_match:
                toodet_pakis = int(toote_paki_match.group(1))
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
            #toote_nimi_match = re.search(r"^(.*?)\s*\d",toode)
            #toote_nimi = toote_nimi_match.group(1).strip() if toote_nimi_match else toode #Juhl kui on nt "24x330ml Saku Originaal" toote nimi
            #ühe_toote_info = [toote_nimi, kogu_maht, toote_protsent]
            toote_nimi = toode_el
            
            
            
            
            
            #Hind poe kohta
            try:
                page.goto(toote_link)
                page.wait_for_selector(".col-span-2.mt-2", timeout=5000)
            except:
                print(f"Poeinfot ei ilmunud: {toote_link}")
                continue
            
            info_supp = BeautifulSoup(page.content(), "html.parser")
            sega_info = info_supp.select_one(".col-span-2.mt-2")

            if not sega_info:
            # Kui ei leia, kuva hoiatus ja toote lehe pealkiri, et näha mis läks valesti
                page_title = info_supp.title.string.strip() if info_supp.title else "No title"
                print(f"Ei leidnud poe infot lehel: {toote_link} — Lehe pealkiri: {page_title}")
                continue  # jätkab järgmise tootega
            
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
                                                        ([\wäöüõ]+) #ühik
                                                        (?:[\s\u00A0\u202F]+aega)? # \u00A0 - nbsp \u202F - nbsp narrrow. Siin vaja millegipärast, muidu annab None vahest
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
                mitmes_tood += 1
                print(f"{mitmes_tood}", end="\r")
                f.write(f"{toote_nimi};{kogu_maht};{toote_protsent};{poe_nimi};{hind};{aeg_ümar};{toote_link}\n")