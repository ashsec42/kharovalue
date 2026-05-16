import requests
import json
import os

# --- CONFIGURATION ---
# Pull tokens securely from GitHub Secrets
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
MAX_BUDGET = 300000 
API_URL = "https://www.marutisuzukitruevalue.com/api/sitecore/CarSearchListing/CarSearchHits"
SEEN_CARS_FILE = "seen_cars.json"

# ... [KEEP EXACTLY THE SAME: get_seen_cars, save_seen_cars, send_telegram_alert functions] ...

def check_true_value():
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
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status() 
        data = response.json()
        
        # Adjust based on your API response
        car_list = data.get('Hits', data) if type(data) is dict else data

        seen_cars = get_seen_cars()
        is_first_run = len(seen_cars) == 0 
        new_cars_found = False

        for car in car_list:
            car_id = str(car.get('vehicleId', car.get('id', car.get('Id'))))
            
            if car_id and car_id not in seen_cars:
                if not is_first_run:
                    send_telegram_alert(car)
                seen_cars.append(car_id)
                new_cars_found = True

        if is_first_run or new_cars_found:
            save_seen_cars(seen_cars)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Removed the 'while True' loop because GitHub handles the scheduling now!
    check_true_value()