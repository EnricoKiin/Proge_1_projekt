# Proge_1_projekt

Autorid: Enrico Kiin ja Tima Matias Juksaar

## Eesmärgid
Luua scraper ostukorvid.ee jaoks, mis käib läbi meie poolt antud kategooriad ning paneb toodete info mingisse tabeltöötlus programmi, et info oleks paremini hallatav.
Ideaalis tahame ka info veebilehele panna, et saaks teiste tudengitega paremini jagada.

## Kasutamine
Kui kasutate seda scraperit, siis ärge pommitage ostukorvid.ee lehekülgi liiga paljude requestidega. Time.sleeid on pandud mõttega sinna, et lehte mitte ülekoormata ning lisaks, et scraper töötaks. Ilma nendeta see throttleib teid ja scraper ei tööta vähemalt 1h aega(testimist saadud teada). Context ja küpsise uuendused on, et leht ei saaks aru, et on scraper, aga IP on sama, et seda scraperit ei saa liiga mitu korda samalt IPlt järjest kasutada ning pole ka vaja, sest info ei uuene nii tihti.

Alguses tehke "pip install requests beautifulsoup4 playwright" ja "playwright install". Veenduge, et teete seda seal, kus teie Pythoni failid on, mida plaanite kasutada. GitHubist saades pole vaja (vist?).

Scraper töötab üldjuhul ilma vigadeta, aga vahest saab töö lõpu poole throttled, et paar viimast toodet võib kaduma minna. Kui juba saad throttled, siis ootab paar tundi ja proovi uuesti.
