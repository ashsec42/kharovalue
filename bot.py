import requests
import json
import os
import time

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
MAX_BUDGET = 160000 

MAIN_PAGE_URL = "https://www.marutisuzukitruevalue.com/used-cars-in-goa/1"
API_URL = "https://www.marutisuzukitruevalue.com/api/sitecore/Menu/GetSearch"
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
        car = item.get('_source', {})
        
        model_name = car.get('name', 'Unknown Model').title()
        mf_year = car.get('mfYear', 'Unknown Year')
        price = car.get('price', 0)
        km_run = car.get('kmRun', 0)
        fuel_type = car.get('fuelType', 'N/A').title()
        transmission = car.get('transmissionType', 'N/A').title()
        owners = car.get('numberOfOwner', 'N/A')
        reg_num = car.get('registrationNumber', 'N/A').upper()
        
        # Pull backend status tags
        booked_date = item.get('BookedDate', None)
        live_status = "⚠️ RESERVED / HOLD" if booked_date else "✅ UNBOOKED (AVAILABLE)"
        
        dealer_name = car.get('dealerName', 'True Value Dealer').title()
        dealer_address = car.get('dealerAddress', '').title()
        exact_location = dealer_address if dealer_address else dealer_name
        
        formatted_price = f"₹ {price:,}" if isinstance(price, (int, float)) else f"₹ {price}"
        formatted_km = f"{km_run:,} km" if isinstance(km_run, (int, float)) else f"{km_run} km"
        
        detail_url = car.get('detailUrl', '')
        car_url = f"https://www.marutisuzukitruevalue.com/buy-car/{detail_url}" if detail_url else MAIN_PAGE_URL

        msg = (
            f"🚀 <b>NEW LISTING DETECTED!</b>\n\n"
            f"🏎️ <b>{model_name} ({mf_year})</b>\n"
            f"📊 <b>Status:</b> {live_status}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 <b>Price:</b> {formatted_price}\n"
            f"🛣️ <b>Mileage:</b> {formatted_km}\n"
            f"⛽ <b>Fuel:</b> {fuel_type}  |  ⚙️ <b>Transmission:</b> {transmission}\n"
            f"👤 <b>Owners:</b> {owners} Owner(s)\n"
            f"🆔 <b>Reg No:</b> {reg_num}\n\n"
            f"🏢 <b>Dealer:</b> {dealer_name}\n"
            f"📍 <b>Location:</b> {exact_location}\n"
            f"━━━━━━━━━━━━━━━━━━━━━"
        )
        
        reply_markup = {
            "inline_keyboard": [
                [{"text": "View Full Listing 🔗", "url": car_url}]
            ]
        }
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": msg,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(reply_markup)
        }
        
        requests.post(url, data=payload, timeout=10)
        print(f"--> Telegram broadcast processed for: {model_name}")
    except Exception as e:
        print(f"--> Failed to send Telegram alert: {e}")

def check_true_value():
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
        # Added direct layout cookie warming call
        session.get(MAIN_PAGE_URL, headers={"User-Agent": headers["User-Agent"]}, timeout=10)
        
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

        # Fixed target endpoint to use menu query mapping structure
        response = session.post(API_URL, headers=headers, json=payload, timeout=15)
        if response.status_code != 200:
            print(f"--> Warning: Server returned code {response.status_code}. Retrying next loop.")
            return

        raw_data = response.json()
        data = json.loads(raw_data) if isinstance(raw_data, str) else raw_data
            
        car_list = data.get('carResult', {}).get('hits', {}).get('hits', [])
        print(f"📡 Current scan sweep: {len(car_list)} matching inventory logs found.")

        seen_cars = get_seen_cars()
        is_first_run = len(seen_cars) == 0 
        new_cars_found = False

        for item in car_list:
            car_id = item.get('_id')
            car_source = item.get('_source', {})
            
            raw_price = car_source.get('price', 9999999)
            try:
                car_price = int(raw_price)
            except (ValueError, TypeError):
                car_price = 9999999
            
            if car_id and car_id not in seen_cars and car_price <= MAX_BUDGET:
                if not is_first_run:
                    send_telegram_alert(item)
                seen_cars.append(car_id)
                new_cars_found = True

        if is_first_run or new_cars_found:
            save_seen_cars(seen_cars)
            print("Database transaction logs synchronized safely.")

    except requests.exceptions.Timeout:
        print("--> Connection timed out while waiting for cluster endpoint. Skipping turn.")
    except Exception as e:
        print(f"--> Execution anomaly: {e}")

if __name__ == "__main__":
    print("🚀 TARGET ACQUIRED: Launching constant live loop tracking (5m intervals)...")
    while True:
        check_true_value()
        time.sleep(300)
