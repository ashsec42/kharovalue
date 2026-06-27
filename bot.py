import requests
import json
import os
import time
import subprocess

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
MAX_BUDGET = 300000 

MAIN_PAGE_URL = "https://www.marutisuzukitruevalue.com/used-cars-in-goa"
MAIN_API_URL = "https://www.marutisuzukitruevalue.com/truevalue/api/graphql"
DEALER_BACKDOOR_URL = "https://www.truevalueofnavelim.com/truevalue/api/graphql"
SEEN_CARS_FILE = "seen_cars.json"

def get_seen_cars():
    if not os.path.exists(SEEN_CARS_FILE) or os.path.getsize(SEEN_CARS_FILE) == 0:
        return []
    with open(SEEN_CARS_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_and_sync_cars(cars_list):
    with open(SEEN_CARS_FILE, 'w') as f:
        json.dump(cars_list, f)
    
    try:
        subprocess.run(["git", "config", "--global", "user.name", "GitHub Actions Bot"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "actions@github.com"], check=True)
        subprocess.run(["git", "add", SEEN_CARS_FILE], check=True)
        
        check_diff = subprocess.run(["git", "diff", "--staged", "--quiet"])
        if check_diff.returncode != 0:
            subprocess.run(["git", "commit", "-m", "Radar Sync: Updated baseline trackers"], check=True)
            subprocess.run(["git", "push"], check=True)
            print("--> State synchronized and pushed to GitHub repository.")
    except Exception as e:
        print(f"--> Git push warning: {e}")

def extract_attribute(attributes_list, target_name):
    for attr in attributes_list:
        if attr.get('name') == target_name:
            return attr.get('value', 'N/A')
    return 'N/A'

def get_unredacted_registration(sku, dealer_code):
    """Hits the local dealer API to bypass corporate data redaction."""
    print(f"   [!] Attempting backdoor fetch for Reg No: {sku}")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Origin": "https://www.truevalueofnavelim.com"
        }
        
        graphql_query = """
        query productSearchByDealers($currentPage: Int = 1, $pageSize: Int = 100, $dealerIds: [String!]) { 
            productSearch( current_page: $currentPage, page_size: $pageSize, phrase: "", filter: [ { attribute: "dealer_code" in: $dealerIds } ] ) { 
                items { 
                    productView { 
                        sku 
                        attributes(roles: []) { name value } 
                    } 
                } 
            } 
        }
        """
        
        payload = {
            "query": graphql_query,
            "variables": {
                "current_page": 1,
                "page_size": 100,
                "dealerIds": [dealer_code]
            }
        }
        
        response = requests.post(DEALER_BACKDOOR_URL, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            items = data.get('data', {}).get('productSearch', {}).get('items', [])
            
            # Find our specific car in the dealer's inventory dump
            for item in items:
                view = item.get('productView', {})
                if view.get('sku') == sku:
                    reg_no = extract_attribute(view.get('attributes', []), 'registration_number')
                    if reg_no != 'N/A':
                        return reg_no.upper()
    except Exception as e:
        print(f"   [!] Backdoor fetch failed: {e}")
        
    return None

def send_telegram_alert(car_view):
    try:
        model_name = car_view.get('name', 'Unknown Model').title()
        sku = car_view.get('sku')
        attributes = car_view.get('attributes', [])
        
        try:
            price = car_view['price']['final']['amount']['value']
        except KeyError:
            price = 0
            
        mf_year = extract_attribute(attributes, 'make_year') 
        km_run = extract_attribute(attributes, 'distance_driven')
        fuel_type = extract_attribute(attributes, 'fuel_type').title()
        transmission = extract_attribute(attributes, 'transmission_type').title()
        owners = extract_attribute(attributes, 'number_of_owners')
        dealer_code = extract_attribute(attributes, 'dealer_code')
        
        # --- STAGE 2: THE SPEAR ---
        # Try to get exact plate, fallback to RTO if blocked
        reg_info = get_unredacted_registration(sku, dealer_code)
        if not reg_info:
            rto = extract_attribute(attributes, 'rto').upper()
            rto_city = extract_attribute(attributes, 'rto_code').title()
            reg_info = f"{rto} ({rto_city})" if rto != 'N/A' else "Unknown RTO"
        else:
            reg_info = f"🚨 <b>{reg_info}</b> 🚨" # Highlight success!
        
        dealer_name = extract_attribute(attributes, 'dealer_name').title()
        dealer_address = extract_attribute(attributes, 'dealer_location').title()
        
        exact_location = dealer_address if dealer_address and dealer_address != 'N/a' else dealer_name
        
        formatted_price = f"₹ {int(price):,}" if price else "Price N/A"
        formatted_km = f"{int(km_run):,} km" if km_run != 'N/A' else "N/A km"
        
        url_key = car_view.get('urlKey', '')
        car_url = f"https://www.marutisuzukitruevalue.com/{url_key}" if url_key else MAIN_PAGE_URL

        msg = (
            f"🚀 <b>NEW LISTING DETECTED UNDER BUDGET!</b>\n\n"
            f"🏎️ <b>{model_name} ({mf_year})</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 <b>Price:</b> {formatted_price}\n"
            f"🛣️ <b>Mileage:</b> {formatted_km}\n"
            f"⛽ <b>Fuel:</b> {fuel_type}  |  ⚙️ <b>Transmission:</b> {transmission}\n"
            f"👤 <b>Owners:</b> {owners} Owner(s)\n"
            f"🆔 <b>Reg/RTO:</b> {reg_info}\n\n"
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
        print(f"--> Rich Telegram alert sent for: {model_name}")
    except Exception as e:
        print(f"--> Failed to send Telegram alert: {e}")

def check_true_value():
    print("1. Initializing browser session...")
    session = requests.Session()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": f"https://www.marutisuzukitruevalue.com/used-cars-in-goa?filters=price%3A0+-+{MAX_BUDGET}"
    }

    # --- STAGE 1: THE NET ---
    graphql_query = f"""
    query ProductSearch {{
      productSearch(
        phrase: ""
        filter: [
          {{ attribute: "price", range: {{ from: 0, to: {MAX_BUDGET} }} }},
          {{ attribute: "car_city", in: ["Goa"] }}
        ]
        sort: [
          {{ attribute: "listing_score", direction: DESC }},
          {{ attribute: "news_from_date", direction: DESC }}
        ]
        page_size: 12
        current_page: 1
      ) {{
        items {{
          productView {{
            id
            name
            sku
            url
            urlKey
            attributes {{
              label
              name
              value
            }}
            ... on SimpleProductView {{
              price {{
                final {{
                  amount {{
                    value
                  }}
                }}
              }}
            }}
          }}
        }}
      }}
    }}
    """

    try:
        print("2. Sending Main GraphQL request...")
        
        params = {
            "query": graphql_query,
            "variables": '{"id":2}'
        }
        
        response = session.get(MAIN_API_URL, headers=headers, params=params, timeout=15)
        print(f"   HTTP Status Code: {response.status_code}")
        response.raise_for_status() 
        
        data = response.json()
        
        car_list = data.get('data', {}).get('productSearch', {}).get('items', [])
        print(f"3. Number of cars identified: {len(car_list)}")

        seen_cars = get_seen_cars()
        is_first_run = len(seen_cars) == 0 
        new_cars_found = False

        for item in car_list:
            car_view = item.get('productView', {})
            car_id = car_view.get('sku') or car_view.get('id')
            
            if not car_id:
                continue

            try:
                car_price = int(car_view['price']['final']['amount']['value'])
            except (KeyError, ValueError, TypeError):
                car_price = 9999999
            
            if car_id not in seen_cars and car_price <= MAX_BUDGET:
                if not is_first_run:
                    send_telegram_alert(car_view)
                seen_cars.append(car_id)
                new_cars_found = True

        if is_first_run or new_cars_found:
            save_and_sync_cars(seen_cars)
            print("4. Local tracking database updated.")
        else:
            print("4. No new inventory updates detected.")

    except requests.exceptions.Timeout:
        print("--> Connection timed out waiting for server response. Skipping this cycle.")
    except Exception as e:
        print(f"CRITICAL SYSTEM ERROR: {e}")

if __name__ == "__main__":
    print("🚀 TARGET ACQUIRED: Launching constant live loop tracking (5m intervals)...")
    while True:
        check_true_value()
        print("💤 Sleeping for 5 minutes...")
        time.sleep(300)
