import requests
import json
import os

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
MAX_BUDGET = 300000 

MAIN_PAGE_URL = "https://www.marutisuzukitruevalue.com/used-cars-in-goa/1"
API_URL = "https://www.marutisuzukitruevalue.com/api/sitecore/CarSearchListing/CarSearchHits"
SEEN_CARS_FILE = "seen_cars.json"

def get_seen_cars():
    if not os.path.exists(SEEN_CARS_FILE):
        return []
    if os.path.getsize(SEEN_CARS_FILE) == 0:
        return []
    with open(SEEN_CARS_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_seen_cars(cars_list):
    with open(SEEN_CARS_FILE, 'w') as f:
        json.dump(cars_list, f)

def send_telegram_alert(item):
    try:
        # Car data is nested inside '_source'
        car = item.get('_source', {})
        
        model_name = car.get('name', 'Unknown Model').title()
        mf_year = car.get('mfYear', 'Unknown Year')
        price = car.get('price', 0)
        
        # Format the price nicely with commas
        formatted_price = f"₹ {price:,}" if isinstance(price, (int, float)) else f"₹ {price}"
        
        # Construct the live URL
        detail_url = car.get('detailUrl', '')
        car_url = f"https://www.marutisuzukitruevalue.com/buy-car/{detail_url}" if detail_url else MAIN_PAGE_URL

        msg = (f"🚨 **NEW LOW PRICE CAR IN GOA** 🚨\n\n"
               f"🚗 **Model:** {model_name} ({mf_year})\n"
               f"💰 **Price:** {formatted_price}\n"
               f"🔗 [View Listing]({car_url})")
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
        print(f"--> Telegram alert sent for: {model_name}")
    except Exception as e:
        print(f"--> Failed to send Telegram alert: {e}")

def check_true_value():
    print("1. Initializing browser session...")
    session = requests.Session()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:150.0) Gecko/20100101 Firefox/150.0",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-US,en;q=0.9",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://www.marutisuzukitruevalue.com",
        "Referer": MAIN_PAGE_URL,
        "Content-Type": "application/json; charset=utf-8"
    }

    try:
        print("2. Warming up session cookies from main page...")
        warmup_response = session.get(MAIN_PAGE_URL, headers={"User-Agent": headers["User-Agent"]})
        warmup_response.raise_for_status()
        
        payload = {
            "dealerCode": [], "fuelType": [], "listingCity": [], "transmissionType": [], 
            "ownertype": [], "kilometers": 10000000, "bookedCars": [], "smartfinanceCars": [], 
            "EbookAvailableCars": [], "certifiedCars": [], 
            "budgetRange": {"Min": 1, "Max": MAX_BUDGET}, 
            "carBodyType": [], "carAge": {"From": 0, "To": 35}, "modeltype": [], 
            "CarCityRange": 1, "CarColor": [], "varientType": [], 
            "sortingFilter": "priceasc", 
            "pageNumber": 0, 
            "dealerCity": ["goa"], 
            "location": {"Lat": "15.2993265", "Lon": "74.12399599999999"}
        }

        print("3. Sending API request with live session tokens...")
        response = session.post(API_URL, headers=headers, json=payload)
        print(f"   HTTP Status Code: {response.status_code}")
        response.raise_for_status() 
        
        raw_data = response.json()
        
        # Double-decode the JSON string if True Value wrapped it in quotes
        if isinstance(raw_data, str):
            data = json.loads(raw_data)
        else:
            data = raw_data
            
        # Navigate the Elasticsearch maze
        car_list = data.get('carResult', {}).get('hits', {}).get('hits', [])
        
        print(f"4. Number of cars identified: {len(car_list)}")

        seen_cars = get_seen_cars()
        is_first_run = len(seen_cars) == 0 
        new_cars_found = False

        for item in car_list:
            # The unique ID sits outside the car details
            car_id = item.get('_id')
            car_source = item.get('_source', {})
            car_price = int(car_source.get('price', 9999999))
            
            # Double check the budget locally just in case their API ignores our payload
            if car_id and car_id not in seen_cars and car_price <= MAX_BUDGET:
                if not is_first_run:
                    send_telegram_alert(item)
                seen_cars.append(car_id)
                new_cars_found = True

        if is_first_run or new_cars_found:
            save_seen_cars(seen_cars)
            print("5. Local tracking database updated.")
        else:
            print("5. No new inventory updates detected.")

    except Exception as e:
        print(f"CRITICAL SYSTEM ERROR: {e}")

if __name__ == "__main__":
    check_true_value()
