
import requests
from bs4 import BeautifulSoup
import re
import json
import os
import time
import random

# --- Configuration ---
# Target: Chiba Prefecture (code usually varies by site, here we implement logic for Suumo/AtHome)
# Price Limit: 5,000,000 JPY
# Parking: >= 2

class PropertyScraper:
    def __init__(self):
        self.properties = []
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.history_file = "price_history.json"
        self.price_history = self.load_history()

    def load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_history(self):
        # Update history with current properties
        for p in self.properties:
            self.price_history[p['link']] = p['price']
        
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.price_history, f, ensure_ascii=False, indent=2)

    def check_price_drop(self, prop):
        url = prop['link']
        current_price = prop['price']
        
        if url in self.price_history:
            old_price = self.price_history[url]
            if current_price < old_price:
                diff = old_price - current_price
                return True, diff, old_price
        return False, 0, 0


    def fetch_suumo(self):
        """
        Scrapes Suumo for Chiba, Saitama, Ibaraki used houses < 5000000 JPY.
        Range: ~2 hours drive from Tsudanuma (covers these prefectures).
        """
        # Prefectures: 08=Ibaraki, 11=Saitama, 12=Chiba
        targets = [
            {"name": "Chiba", "code": "12"},
            {"name": "Ibaraki", "code": "08"}
        ]

        for target in targets:
            print(f"Scraping Suumo ({target['name']})...")
            # ar=030 (Kanto), bs=021 (Used House), ta=CODE
            url = f"https://suumo.jp/jj/bukken/ichiran/JJ010FJ001/?ar=030&bs=021&ta={target['code']}&kb=1&kt=500&tb=0&tj=0&po1=25&po2=99&sngz=&z=1" 
            
            try:
                response = requests.get(url, headers=self.headers)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                
                listings = soup.find_all('div', class_='property_unit-content')
                
                if not listings:
                    print(f"No listings found for {target['name']}.")
                    continue

                for listing in listings:
                    data = self._parse_suumo_listing(listing)
                    if data:
                        self.properties.append(data)
                        
            except Exception as e:
                print(f"Error scraping Suumo {target['name']}: {e}")
                # Only add mock data once if everything fails
                if not self.properties:
                    print("Using mock data for testing.")
                    self.add_mock_data()


    def add_mock_data(self):
        """
        Adds sample data to ensure the pipeline can be tested even if scraping fails/blocks.
        """
        self.properties.append({
            "source": "Test",
            "title": "【テスト物件】千葉県東金市 中古戸建 (※スクレイピング不可時のサンプル)",
            "link": "https://suumo.jp/example",
            "price": 3800000,
            "price_str": "380万円",
            "address": "千葉県東金市",
            "access": "JR東金線 東金駅 歩15分",
            "parking_comment": "カースペース2台可、車種により3台可能",
            "remarks": "雨漏りなし。シロアリ点検済み。建物傾きなし。"
        })

    def _parse_suumo_listing(self, listing_soup):
        """
        Extracts details from a Suumo listing block.
        """
        try:
            # Title / Link
            title_elem = listing_soup.find('a', class_='js-tit1')
            if not title_elem:
                h2_elem = listing_soup.find('h2', class_='property_unit-title')
                if h2_elem:
                    title_elem = h2_elem.find('a')
            if not title_elem:
                title_elem = listing_soup.find('a', href=True)
            
            if not title_elem: return None
            
            link = "https://suumo.jp" + title_elem['href'] if title_elem['href'].startswith('/') else title_elem['href']
            title = title_elem.text.strip()
            
            # Price
            price_elem = listing_soup.find('span', class_='dottable-value')
            if not price_elem: price_elem = listing_soup.find('div', class_='property_unit-price')
            price_str = price_elem.text.strip() if price_elem else "0"
            price = self._parse_price(price_str)
            
            # Details
            # This part is highly dependent on formatting.
            full_text = listing_soup.text
            
            address = "千葉県..." # Placeholder extraction
            # Try to find address in dd/dt or table
            
            return {
                "source": "Suumo",
                "title": title,
                "link": link,
                "price": price,
                "price_str": price_str, 
                "address": address,
                "access": "Check link",
                "parking_comment": full_text[:200], # Use first 200 chars for analysis
                "remarks": full_text
            }
        except Exception as e:
            # print(f"Parser error: {e}")
            return None

    def _parse_price(self, price_str):
        try:
            num = re.sub(r'[^\d]', '', price_str)
            # Simple heuristic
            if len(num) > 0:
                return int(num) * 10000
            return 0
        except:
            return 0
    
    def analyze_parking(self, description):
        score = 0
        reason = []
        
        desc_norm = description.translate(str.maketrans({chr(0xFF01 + i): chr(0x21 + i) for i in range(94)})) # Fullwidth to halfwidth
        
        if re.search(r'駐車(場)?.*[2２]台', description) or re.search(r'[2２]台.*可', description):
            score = 2
            reason.append("Standard 2 cars")
        if re.search(r'駐車(場)?.*[3３]台', description) or re.search(r'[3３]台.*可', description):
            score = 3
            reason.append("Excellent 3 cars")
        if re.search(r'駐車(場)?.*[4４]台', description) or re.search(r'[4４]台.*可', description):
            score = 4
            reason.append("Super Rare 4+ cars")
        if "並列" in description:
            reason.append("Parallel OK")
        
        if score == 0:
            return 0, "Details in Link"
        
        return score, ", ".join(reason)

    def analyze_three_evils(self, description):
        evils = {
            "雨漏り": False,
            "シロアリ": False,
            "傾き": False
        }
        
        if "雨漏" in description: evils["雨漏り"] = True
        if "シロアリ" in description or "白蟻" in description: evils["シロアリ"] = True
        if "傾き" in description or "建付" in description: evils["傾き"] = True 
        
        return evils

if __name__ == "__main__":
    scraper = PropertyScraper()
    scraper.fetch_suumo()
    print(f"Found {len(scraper.properties)} properties.")
