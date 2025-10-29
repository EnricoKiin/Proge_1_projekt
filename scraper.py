#Alguses tee pip install requests beautifulsoup4 selenium terminalis. Muidu ei tööta

# class=ml-1.w-full selles on kogu info
import requests
from bs4 import BeautifulSoup
from selenium import webdriver


sitemap_url = "https://ostukorvid.ee/sitemap.xml"
sitemap_info = requests.get(sitemap_url)
sitemap_soup = BeautifulSoup(sitemap_info.content, "xml")
kategooriad = [loc.text for loc in sitemap_soup.find_all("loc")]
scrape = [olu, viin, siider, vein]
#print(kategooriad)
driver = webdriver.Chrome() # Ütleme mis brauserit me kasutame
driver.get("https://ostukorvid.ee/kategooriad/olu?price=unit") # Ava veebileht