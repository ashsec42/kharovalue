import requests
import json
import os

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
MAX_BUDGET = 300000 
API_URL = "https://www.marutisuzukitruevalue.com/api/sitecore/CarSearchListing/CarSearchHits"
SEEN_CARS_FILE = "seen_cars.json"

def get_seen_cars():
    if not os.path.exists(SEEN_CARS_FILE):
        return []
    # Safety check in case the file is completely empty (0 bytes)
    if os.path.getsize(SEEN_CARS_FILE) == 0:
        return []
    with open(SEEN_CARS_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return [] # If the JSON is broken, start fresh

def save_seen_cars(cars_list):
    with open(SEEN_CARS_FILE, 'w') as f:
        json.dump(cars_list, f)

def send_telegram_alert(car):
    try:
        model_name = car.get('carName', car.get('Model', 'Unknown Model'))
        price = car.get('Price', car.get('price', 'Unknown Price'))
        car_url = car.get('url', f"https://www.marutisuzukitruevalue.com/buy-car/{car.get('id', '')}")

        msg = (f"🚨 **NEW LOW PRICE CAR IN GOA** 🚨\n\n"
               f"🚗 **Model:** {model_name}\n"
               f"💰 **Price:** ₹ {price}\n"
               f"🔗 [View Listing]({car_url})")
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
        print(f"--> Successfully sent Telegram alert for: {model_name}")
    except Exception as e:
        print(f"--> Failed to send Telegram message: {e}")

def check_true_value():
    print("1. Starting True Value check...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/json; charset=utf-8",
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://www.marutisuzukitruevalue.com",
        "Referer": "https://www.marutisuzukitruevalue.com/used-cars-in-goa/1"
    }

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

    try:
        print("2. Sending request to True Value API...")
        response = requests.post(API_URL, headers=headers, json=payload)
        print(f"   HTTP Status Code: {response.status_code}")
        response.raise_for_status() 
        
        data = response.json()
        print("3. Successfully parsed JSON data from website.")
        
        # Check exactly what the API returned
        if 'Hits' in data:
            car_list = data['Hits']
            print("   Found 'Hits' array in the data.")
        elif type(data) is list:
            car_list = data
            print("   Data is a direct list.")
        else:
            car_list = data.get('data', [])
            print("   Fell back to 'data' key or empty list.")

        print(f"4. Number of cars found under budget: {len(car_list)}")

        seen_cars = get_seen_cars()
        print(f"5. Cars already in memory: {len(seen_cars)}")
        
        is_first_run = len(seen_cars) == 0 
        new_cars_found = False

        for car in car_list:
            car_id = str(car.get('vehicleId', car.get('id', car.get('Id'))))
            if car_id and car_id not in seen_cars:
                print(f"   [!] NEW CAR ID DETECTED: {car_id}")
                if not is_first_run:
                    send_telegram_alert(car)
                seen_cars.append(car_id)
                new_cars_found = True

        if is_first_run or new_cars_found:
            save_seen_cars(seen_cars)
            print("6. Saved updated memory to seen_cars.json")
        else:
            print("6. No new memory to save.")

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    check_true_value()
