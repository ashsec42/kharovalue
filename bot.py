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
    except Exception as e:
        print(f"--> Git push warning: {e}")

def extract_attribute(attributes_list, target_name):
    for attr in attributes_list:
        if attr.get('name') == target_name:
            return attr.get('value', 'N/A')
    return 'N/A'

def get_unredacted_details(sku, dealer_code):
    """Fetches registration number and dealer phone from the local dealer API."""
    try:
        headers = {"Content-Type": "application/json"}
        graphql_query = """
        query productSearchByDealers($dealerIds: [String!]) { 
            productSearch(filter: [{ attribute: "dealer_code" in: $dealerIds }]) { 
                items { productView { sku attributes(roles: []) { name value } } } 
            } 
        }
        """
        payload = {"query": graphql_query, "variables": {"dealerIds": [dealer_code]}}
        response = requests.post(DEALER_BACKDOOR_URL, headers=headers, json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            items = data.get('data', {}).get('productSearch', {}).get('items', [])
            for item in items:
                view = item.get('productView', {})
                if view.get('sku') == sku:
                    attrs = view.get('attributes', [])
                    reg_no = extract_attribute(attrs, 'registration_number')
                    dealer_info_json = extract_attribute(attrs, 'dealer_additional_info')
                    phone = "N/A"
                    if dealer_info_json != 'N/A':
                        phone = json.loads(dealer_info_json).get('phone', 'N/A')
                    return reg_no.upper() if reg_no != 'N/A' else None, phone
    except Exception as e:
        print(f"   [!] Backdoor fetch failed: {e}")
    return None, "N/A"

def send_telegram_alert(car_view):
    try:
        model_name = car_view.get('name', 'Unknown Model').title()
        sku = car_view.get('sku')
        attrs = car_view.get('attributes', [])
        dealer_code = extract_attribute(attrs, 'dealer_code')
        
        # Extract new details
        reg_no, dealer_phone = get_unredacted_details(sku, dealer_code)
        reg_display = f"🚨 <b>{reg_no}</b> 🚨" if reg_no else extract_attribute(attrs, 'rto').upper()
        added_date = extract_attribute(attrs, 'news_from_date')
        
        price = car_view.get('price', {}).get('final', {}).get('amount', {}).get('value', 0)
        
        msg = (
            f"🚀 <b>NEW LISTING!</b>\n\n"
            f"🏎️ <b>{model_name}</b>\n"
            f"💰 <b>Price:</b> ₹ {int(price):,}\n"
            f"🆔 <b>Reg No:</b> {reg_display}\n"
            f"📅 <b>Listed On:</b> {added_date}\n"
            f"📞 <b>Dealer Phone:</b> {dealer_phone}\n"
        )
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print(f"--> Failed to send alert: {e}")

# ... (rest of check_true_value logic remains the same)
