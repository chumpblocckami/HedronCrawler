from threading import local
from bs4 import BeautifulSoup
import requests
import urllib 
import socket
import datetime as dt 
import time 
import random 
from tqdm import tqdm

class Crawler():
    def __init__(self):
        self.ip = None
        self.endpoint = "https://www.mtggoldfish.com"
        self.tournaments = []
        self.results = []
        self.decks = []

    def load_ip(self):
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        print(f"hostname: {hostname}, local_ip:{local_ip}")
        self.ip = local_ip

    def crawl_tournaments(self):
        """
            Load tournaments from MTGoldfish.
            This methods use somewhat a bruteforce approach to query of all mtg tournament stored in MTGoldfish.
            The idea is that we continue to crawl data that we didn't download, so a check is mandatory
        """
        day,month,year = dt.datetime.now().day,dt.datetime.now().month,dt.datetime.now().year
        for idx in range(1,5): #prob a nice number is 200
            url = f"https://www.mtggoldfish.com/tournament_searches/create?commit=Search&page={idx}&tournament_search%5Bdate_range%5D=11%2F22%2F2005+-+{month}%2F{day}%2F{year}&tournament_search%5Bformat%5D=pauper&tournament_search%5Bname%5D=&utf8=%E2%9C%93"
            page = urllib.request.urlopen(url)
            deck_soup = BeautifulSoup(page.read(),features="lxml")
            page_tournament = [f"{self.endpoint}{a['href']}" for a in deck_soup.findAll("a",href=True) if "tournament" in a["href"]]
            self.tournaments.extend(page_tournament)
            time.sleep(1/random.randint(1,10))

    def crawl_results(self,url):
        """Crawl tournament info, expecially deck links"""
        data = []
        labels = "placement,deck,player,dollar,tix,_,deck_url,player_url,_,tournament_name".split(",")

        tournament_soup = BeautifulSoup(requests.get(url).text,features="lxml")
        tournament_name = tournament_soup.find("h2").text
        for tr in tournament_soup.find("table").find_all("tr"):
            attributes = [x.text.strip() for x in tr.find_all("td")]
            if len(attributes) <= 1:
                continue
            else:
                attributes.extend(["https://mtggoldfish.com"+x["href"] for x in tr.find_all("a",href=True)])
                attributes.extend([tournament_name])
                raw_data = {k:v for k,v in zip(labels,attributes)}
                try:
                    del raw_data["_"] 
                except:
                    print(url)
                    continue
                data.append(raw_data)
        time.sleep(1/random.randint(1,10))
        self.results.append(data)

    def crawl_deck(self,url):
        """Crawl decks"""
        page = urllib.request.urlopen(url)
        deck_soup = BeautifulSoup(page.read(),features="lxml")

        deck = {}

        deck["deck_name"] = "".join(deck_soup.find("h1").text.strip().split("by")[0]).strip()
        deck["author"] = "".join(deck_soup.find("h1").text.strip().split("by")[1]).strip()
        information = deck_soup.find("p", {"class":"deck-container-information"}).text.split("\n\n")
        deck["format"] = "".join(information[0].split(": ")[1]).strip()
        deck["event"] = "".join(information[1].split(", ")[0]).replace("Event: ","").strip()
        deck["place"] = "".join(information[1].split(", ")[1]).strip()
        deck["score"] = "".join(information[1].split(", ")[2]).strip()
        deck["date"] = "".join(information[3].split(": ")[1]).replace(",","").strip()
        deck["archetype"] = "".join(information[4].split(": ")[1]).strip()

        cards = [x.text.strip() for x in deck_soup.find("table").find_all("a")]
        quantities = [int(x.text.strip()) for x in deck_soup.find("table").find_all("td",{"class":"text-right"}) if len(x.text.strip()) < 2]
        mainboard = {}
        sideboard={}
        count = 0
        for card,quantity in zip(cards,quantities):
                count = count + quantity
                if count > 60:
                    sideboard[card] = quantity
                else:
                    mainboard[card] = quantity

        deck["main"] = mainboard
        deck["sideboard"] = sideboard
        self.decks.append(deck)

    def start_crawl(self):
        """
            Entrypoint of the crawler, that is composed by 3 steps:
            1. Crawl of the tournament from the search page
            2. Crawl of the results from each results page
            3. Crawl of the decks from each results page

        """
        self.load_ip()

        self.crawl_tournaments()
        print(f"Number of tournaments {len(self.tournaments)}")

        for tournament in tqdm(self.tournaments,desc="Crawling tournaments..."):
            self.crawl_results(url=tournament)
        print(f"Number of results {len(self.results)}")

        for deck_url in tqdm(self.decks,desc="Crawling decks..."):
            self.crawl_deck(url=deck_url)
        print(f"Number of decks {len(self.decks)}")

if __name__ == "__main__":
    hedron_crawler = Crawler()
    hedron_crawler.start_crawl()
