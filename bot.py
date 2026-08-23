import requests
import json
import os

# --- Constants & Configuration ---
# Your Telegram credentials and max budget limit
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
MAX_BUDGET = 200000 # Your 2 Lakh limit

API_URL = "https://www.marutisuzukitruevalue.com/truevalue/api/graphql"
DB_FILE = "seen_cars.json"

# --- Database Functions ---
def get_seen_cars():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

def save_and_sync_cars(cars):
    with open(DB_FILE, 'w') as f:
        json.dump(cars, f)

# --- Helper Functions ---
def extract_attribute(attributes_list, attr_name):
    """Pulls a specific filter out of Maruti's giant attribute array."""
    for attr in attributes_list:
        if attr.get('name') == attr_name:
            return attr.get('value', 'N/A')
    return "N/A"

def send_telegram_alert(car_view):
    """Formats and fires the alert to your Telegram."""
    attributes = car_view.get('attributes', [])
    
    # Extract the exact details you care about
    name = car_view.get('name', 'Unknown Car')
    price = car_view.get('price', {}).get('final', {}).get('amount', {}).get('value', 'Price Unknown')
    kms = extract_attribute(attributes, 'distance_driven')
    year = extract_attribute(attributes, 'make_year')
    dealer = extract_attribute(attributes, 'dealer_location')
    dealer_phone = "Check dealer profile" 
    
    # Try to extract the phone number from the messy JSON string
    dealer_info_str = extract_attribute(attributes, 'dealer_additional_info')
    if dealer_info_str != 'N/A':
        try:
            info_dict = json.loads(dealer_info_str)
            dealer_phone = info_dict.get('phone', dealer_phone).strip()
        except:
            pass

    url = car_view.get('url', 'https://www.marutisuzukitruevalue.com/used-cars-in-goa')

    message = (
        f"🚨 <b>New True Value Car in Goa!</b> 🚨\n\n"
        f"🚗 <b>{name}</b> ({year})\n"
        f"💰 Price: ₹{price:,}\n"
        f"🛣️ KMS Driven: {kms}\n"
        f"📍 Dealer: {dealer}\n"
        f"📞 Phone: {dealer_phone}\n\n"
        f"<a href='{url}'>View Car Listing</a>"
    )

    telegram_api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }

    try:
        requests.post(telegram_api_url, json=payload, timeout=10)
    except Exception as e:
        print(f"Failed to send Telegram alert: {e}")

# --- The Main Engine (Patched for the new API!) ---
def check_true_value():
    print("1. Initializing session...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }

    # The new GET-based GraphQL query.
    # Note: I swapped 'car_city: ["Goa"]' with your specific Madgaon & Verna dealer codes to keep it localized.
    # If you want ALL of Goa, change dealer_code back to car_city.
    graphql_query = f"""
    query ProductSearch {{ 
        productSearch(
            phrase: "" 
            filter: [
                {{ attribute: "price", range: {{ from: 0, to: {MAX_BUDGET} }} }}, 
                {{ attribute: "dealer_code", in: ["50668-MGA-CHOWG", "50366-VRN-SAI", "50091-DPR-CHOWG"] }}
            ] 
            sort: [{{ attribute: "price", direction: ASC }}] 
            page_size: 100 
            current_page: 1
        ) {{ 
            items {{ 
                productView {{ 
                    inStock 
                    name 
                    sku 
                    url 
                    attributes {{ name value }} 
                    images {{ url }} 
                    ... on SimpleProductView {{ 
                        price {{ 
                            final {{ amount {{ value }} }} 
                        }} 
                    }} 
                }} 
            }} 
        }} 
    }}
    """

    params = {
        "query": graphql_query,
        "variables": '{"id":2}'
    }

    try:
        print("2. Sending GET request...")
        response = requests.get(API_URL, headers=headers, params=params, timeout=15)
        response.raise_for_status() 
        data = response.json()
        
        car_list = data.get('data', {}).get('productSearch', {}).get('items', [])
        print(f"3. Found {len(car_list)} cars matching criteria.")

        seen_cars = get_seen_cars()
        is_first_run = len(seen_cars) == 0 
        new_cars_found = False

        for item in car_list:
            car_view = item.get('productView', {})
            car_id = car_view.get('sku')
            
            if not car_id:
                continue

            try:
                car_price = int(car_view['price']['final']['amount']['value'])
            except:
                car_price = 9999999
            
            if car_id not in seen_cars and car_price <= MAX_BUDGET:
                # We skip sending alerts on the very first run so you don't get spammed with 40 old cars
                if not is_first_run:
                    send_telegram_alert(car_view)
                
                seen_cars.append(car_id)
                new_cars_found = True

        if is_first_run or new_cars_found:
            save_and_sync_cars(seen_cars)
            print("4. Database updated.")
        else:
            print("4. No new cars found this cycle.")

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    check_true_value()
