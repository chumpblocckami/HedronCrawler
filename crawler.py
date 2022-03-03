import datetime as dt
import json
import os
import random
import socket
import string
import time
import urllib

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm


class Crawler():
    def __init__(self, from_date, to_date):

        self.start_date = from_date
        self.end_date = to_date

        self.ip = None
        self.stoarge_path = "database"
        self.save_path = f"{self.stoarge_path}/{str(self.start_date).split(' ')[0]}-{str(self.end_date).split(' ')[0]}"
        self.endpoint = "http://www.mtggoldfish.com/"

        self.tournaments = []
        self.decks = []

    def load_ip(self):
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        print(f"hostname: {hostname}, local_ip:{local_ip}")
        self.ip = local_ip

    def load_env(self):
        if self.stoarge_path not in os.listdir():
            os.mkdir(f"{self.stoarge_path}")
        if self.save_path.split("/")[1] not in os.listdir(self.stoarge_path):
            os.mkdir(self.save_path)
            os.mkdir(f"{self.save_path}/deck")
            os.mkdir(f"{self.save_path}/tournament")

    def crawl_tournaments(self):
        """
            Load tournaments from MTGoldfish.
            This methods use somewhat a bruteforce approach to query of all mtg tournament stored in MTGoldfish.
            The idea is that we continue to crawl data that we didn't download, so a check is mandatory
        """
        from_day, from_month, from_year = self.start_date.day, self.start_date.month, self.start_date.year
        to_day, to_month, to_year = self.end_date.day, self.end_date.month, self.end_date.year
        idx = 1
        while True:
            try:
                url = f"https://www.mtggoldfish.com/tournament_searches/create?commit=Search&page={idx}&tournament_search%5Bdate_range%5D={from_month}%2F{from_day}%2F{from_year}+-+{to_month}%2F{to_day}%2F{to_year}&tournament_search%5Bformat%5D=pauper&tournament_search%5Bname%5D=&utf8=%E2%9C%93"
                page = urllib.request.urlopen(url)
                deck_soup = BeautifulSoup(page.read(), features="lxml")
                page_tournament = [f"{self.endpoint}{a['href']}" for a in deck_soup.findAll("a", href=True) if "tournament" in a["href"]]
                self.tournaments.extend(page_tournament)
                time.sleep(1 / random.randint(1, 10))
                idx = idx + 1
                if "No tournaments found." in [x.text.strip() for x in deck_soup.findAll("p")] or idx > 5:
                    return
            except Exception as specific_exception:
                print(f"{specific_exception}")
                return

    def crawl_results(self, url):
        """Crawl tournament info, expecially deck links"""
        data = []
        labels = "placement,deck,player,dollar,tix,_,deck_url,player_url,_,tournament_name".split(",")

        tournament_soup = BeautifulSoup(requests.get(url).text, features="lxml")
        tournament_name = tournament_soup.find("h2").text
        for tr in tournament_soup.find("table").find_all("tr"):
            attributes = [x.text.strip() for x in tr.find_all("td")]
            if len(attributes) <= 1:
                continue
            else:
                attributes.extend([self.endpoint + x["href"] for x in tr.find_all("a", href=True)])
                attributes.extend([tournament_name])
                raw_data = {k: v for k, v in zip(labels, attributes)}
                try:
                    del raw_data["_"]
                except:
                    continue
                self.decks.append(raw_data["deck_url"])
                data.append(raw_data)
        time.sleep(1 / random.randint(1, 10))
        json_name = tournament_name.translate(str.maketrans('', '', string.punctuation)).replace(" ", "_").lower()
        try:
            with open(f"{self.save_path}/tournament/{json_name}.json", "w+") as saver:
                json.dump({f"{tournament_name}": data}, saver)
        except Exception as save_error:
            print(f"Cannot save tournament {json_name}\t{save_error}")

    def crawl_deck(self, url):
        """Crawl decks"""
        try:
            page = urllib.request.urlopen(url)
        except:
            return
        else:
            deck_soup = BeautifulSoup(page.read(), features="lxml")

            deck = {}
            deck["url"] = url
            deck["name"] = "".join(deck_soup.find("h1").text.strip().split("by")[0]).strip()
            deck["author"] = "".join(deck_soup.find("h1").text.strip().split("by")[1]).strip()
            raw_info = [x for x in deck_soup.find("p", {"class": "deck-container-information"}).text.split("\n\n") if x != '']
            info = {x.replace("\n", "").split(":")[0].replace(" ", "_").lower(): x.replace("\n", "").split(":")[1].strip() for x in raw_info if
                    ":" in x}
            deck.update(info)

            cards = [x.text.strip() for x in deck_soup.find("table").find_all("a")]
            quantities = [int(x.text.strip()) for x in deck_soup.find("table").find_all("td", {"class": "text-right"}) if len(x.text.strip()) <= 2]
            try:
                assert sum(quantities) >= 75
            except AssertionError:
                print(f"{url}: deck+side is less than 75!")
                return
            mainboard = {}
            sideboard = {}
            count = 0
            for card, quantity in zip(cards[::-1], quantities[::-1]):
                if count >= 15:
                    mainboard[card] = quantity
                else:
                    sideboard[card] = quantity
                count = count + quantity

            deck["main"] = mainboard
            deck["sideboard"] = sideboard
            deck_name = f"{deck['name']}-{deck['author']}-{deck['event']}".translate(str.maketrans('', '', string.punctuation)).replace(" ",
                                                                                                                                        "_").lower()
            try:
                with open(f"{self.save_path}/deck/{deck_name}.json", "w+") as saver:
                    json.dump(deck, saver)
            except Exception as save_error:
                print(f"Cannot save deck {deck_name}\t{save_error}")
            time.sleep(random.uniform(1, 5))

    def start_crawl(self, ):
        """
            Entrypoint of the crawler, that is composed by 3 steps:
            1. Crawl of the tournament from the search page
            2. Crawl of the results from each results page
            3. Crawl of the decks from each results page

        """
        self.load_ip()

        self.load_env()

        self.crawl_tournaments()
        print(f"Number of tournaments {len(self.tournaments)}")

        for tournament in tqdm(self.tournaments, desc="Crawling tournaments..."):
            self.crawl_results(url=tournament)
        print(f"Number of results {len(self.decks)}")

        for deck_url in tqdm(self.decks, desc="Crawling decks..."):
            self.crawl_deck(url=deck_url)
        print(f"Number of decks {len(self.decks)}")


if __name__ == "__main__":
    hedron_crawler = Crawler(from_date=dt.datetime(day=1, month=1, year=2021),
                             to_date=dt.datetime(day=15, month=1, year=2021))
    hedron_crawler.start_crawl()
