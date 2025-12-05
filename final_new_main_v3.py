import requests
import json
from datetime import datetime, timedelta
import time
import random

# === Credentials ===
CORE_ACCOUNT_ID = "3384f900-b8b1-41bc-8324-1e6000e897ec"
CORE_APP_KEY = "c1bf7dbf-5365-9d50-95a1-960ee4455445"
INPOST_API_KEY = "da3f39f46c9f473d29cc8ec40a0ae787"

core_headers = {
    "Content-Type": "application/json",
    "api-auth-accountid": CORE_ACCOUNT_ID,
    "api-auth-applicationkey": CORE_APP_KEY
}

inpost_headers = {
    "Content-Type": "application/json"
}

# --- Dear Systems rate-limit helpers ---
_DEAR_LAST_CALL_AT = 0.0
_DEAR_MIN_INTERVAL = 0.35  # seconds between Dear calls (tune 0.25–0.5)

def _dear_rate_limit():
    """Simple per-process pacing to avoid burst requests to Dear endpoints."""
    global _DEAR_LAST_CALL_AT
    now = time.time()
    delta = now - _DEAR_LAST_CALL_AT
    if delta < _DEAR_MIN_INTERVAL:
        time.sleep(_DEAR_MIN_INTERVAL - delta)
    _DEAR_LAST_CALL_AT = time.time()

def dear_request(method, url, *, headers=None, json=None, params=None, timeout=75,
                 max_retries=5, backoff_base=0.5, max_sleep=15.0):
    """
    HTTP request with retry/backoff for Dear (handles 429/5xx & Retry-After).
    Returns the final requests.Response.
    """
    last_resp = None
    for attempt in range(1, max_retries + 1):
        _dear_rate_limit()
        resp = requests.request(method, url, headers=headers, json=json, params=params, timeout=timeout)
        last_resp = resp

        if resp.status_code in (429, 500, 502, 503, 504):
            retry_after = resp.headers.get("Retry-After")
            if retry_after:
                try:
                    delay = float(retry_after)
                except ValueError:
                    delay = backoff_base * (2 ** (attempt - 1)) + random.uniform(0, 0.25)
            else:
                delay = backoff_base * (2 ** (attempt - 1)) + random.uniform(0, 0.25)

            if attempt >= max_retries:
                return resp

            time.sleep(min(delay, max_sleep))
            continue

        return resp

    return last_resp


def get_core_sale(sale_id):
    """
    Fetch the complete sale object using the /v2/sale endpoint.

    This endpoint (with CombineAdditionalCharges=true) returns:
      - Root-level sale fields (Customer, Email, ShippingAddress, Fulfilments, etc.)
      - Nested "Order" section with "SaleOrderNumber" and "Lines". fileciteturn2file0

    We normalise this into a compact structure that the rest of the script uses.
    """
    url = f"https://inventory.dearsystems.com/ExternalApi/v2/sale?ID={sale_id}&CombineAdditionalCharges=true"
    print(f"DEBUG: Fetching complete sale data from URL: {url}")

    response = dear_request("GET", url, headers=core_headers)

    if response.status_code != 200:
        print(f"❌ Error fetching complete sale {sale_id}: {response.status_code} - {response.text}")
        return {}

    try:
        sale_root = response.json()
    except Exception as e:
        print(f"❌ Failed to decode JSON for sale {sale_id}: {e}")
        return {}

    # Basic sanity check
    if not isinstance(sale_root, dict) or "ID" not in sale_root:
        print(f"❌ Invalid response structure for sale {sale_id}")
        return {}

    # Dear's /v2/sale response has a nested "Order" block that holds SaleOrderNumber and Lines.
    order_section = sale_root.get("Order") or {}

    return {
        # Order-level data (SaleOrderNumber, Lines, totals, etc.)
        "Order": order_section,

        # Internal sale identifier (root ID or SaleID if present)
        "ID": sale_root.get("ID") or sale_root.get("SaleID"),

        # Root-level shipping address (the one you showed in your sample JSON)
        "ShippingAddress": sale_root.get("ShippingAddress") or {},

        # Customer contact details
        "Email": sale_root.get("Email") or sale_root.get("CustomerEmail"),
        "Phone": sale_root.get("Phone") or sale_root.get("CustomerPhone"),
        "Customer": sale_root.get("Customer") or sale_root.get("CustomerName"),

        # Ship-by date: prefer explicit ShipBy, fall back to sale/order dates if necessary
        "ShipBy": sale_root.get("ShipBy")
                  or sale_root.get("ShipByDate")
                  or order_section.get("SaleOrderDate"),

        # Keep the full raw payload for any future debugging
        "Raw": sale_root,
    }


def get_fulfillment_status(sale_id):
    """Get actual fulfillment status from the fulfillment endpoint."""
    url = f"https://inventory.dearsystems.com/ExternalApi/v2/sale/fulfilment?SaleID={sale_id}"
    try:
        response = dear_request("GET", url, headers=core_headers)
        print(f"📥 Fulfillment API response status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"📥 Fulfillment data: {json.dumps(data, indent=2)[:500]}...")
            return data
        else:
            print(f"❌ Fulfillment API error: {response.status_code} - {response.text}")
        return {}
    except Exception as e:
        print(f"❌ Error fetching fulfillment status: {str(e)}")
        return {}

def get_country_code(country_name):
    return {
        "Poland": "PL", "Germany": "DE", "France": "FR", "United Kingdom": "GB", "Ireland": "IE",
        "Italy": "IT", "Spain": "ES", "Netherlands": "NL", "Belgium": "BE", "Luxembourg": "LU", "Denmark": "DK",
        # Additional countries
        "Afghanistan": "AF",
        "Albania": "AL",
        "Algeria": "DZ",
        "Andorra": "AD",
        "Angola": "AO",
        "Antigua and Barbuda": "AG",
        "Argentina": "AR",
        "Armenia": "AM",
        "Australia": "AU",
        "Austria": "AT",
        "Azerbaijan": "AZ",
        "Bahamas": "BS",
        "Bahrain": "BH",
        "Bangladesh": "BD",
        "Barbados": "BB",
        "Belarus": "BY",
        "Belize": "BZ",
        "Benin": "BJ",
        "Bhutan": "BT",
        "Bolivia": "BO",
        "Bosnia and Herzegovina": "BA",
        "Botswana": "BW",
        "Brazil": "BR",
        "Brunei": "BN",
        "Bulgaria": "BG",
        "Burkina Faso": "BF",
        "Burundi": "BI",
        "Cabo Verde": "CV",
        "Cambodia": "KH",
        "Cameroon": "CM",
        "Canada": "CA",
        "Central African Republic": "CF",
        "Chad": "TD",
        "Chile": "CL",
        "China": "CN",
        "Colombia": "CO",
        "Comoros": "KM",
        "Congo, Democratic Republic of the": "CD",
        "Congo, Republic of the": "CG",
        "Costa Rica": "CR",
        "Croatia": "HR",
        "Cuba": "CU",
        "Cyprus": "CY",
        "Czech Republic": "CZ",
        "Djibouti": "DJ",
        "Dominica": "DM",
        "Dominican Republic": "DO",
        "Ecuador": "EC",
        "Egypt": "EG",
        "El Salvador": "SV",
        "Equatorial Guinea": "GQ",
        "Eritrea": "ER",
        "Estonia": "EE",
        "Eswatini": "SZ",
        "Ethiopia": "ET",
        "Fiji": "FJ",
        "Finland": "FI",
        "Gabon": "GA",
        "Gambia": "GM",
        "Georgia": "GE",
        "Ghana": "GH",
        "Greece": "GR",
        "Grenada": "GD",
        "Guatemala": "GT",
        "Guinea": "GN",
        "Guinea-Bissau": "GW",
        "Guyana": "GY",
        "Haiti": "HT",
        "Honduras": "HN",
        "Hungary": "HU",
        "Iceland": "IS",
        "India": "IN",
        "Indonesia": "ID",
        "Iran": "IR",
        "Iraq": "IQ",
        "Israel": "IL",
        "Jamaica": "JM",
        "Japan": "JP",
        "Jordan": "JO",
        "Kazakhstan": "KZ",
        "Kenya": "KE",
        "Kiribati": "KI",
        "Korea, North": "KP",
        "Korea, South": "KR",
        "Kuwait": "KW",
        "Kyrgyzstan": "KG",
        "Laos": "LA",
        "Latvia": "LV",
        "Lebanon": "LB",
        "Lesotho": "LS",
        "Liberia": "LR",
        "Libya": "LY",
        "Liechtenstein": "LI",
        "Lithuania": "LT",
        "Madagascar": "MG",
        "Malawi": "MW",
        "Malaysia": "MY",
        "Maldives": "MV",
        "Mali": "ML",
        "Malta": "MT",
        "Marshall Islands": "MH",
        "Mauritania": "MR",
        "Mauritius": "MU",
        "Mexico": "MX",
        "Micronesia": "FM",
        "Moldova": "MD",
        "Monaco": "MC",
        "Mongolia": "MN",
        "Montenegro": "ME",
        "Morocco": "MA",
        "Mozambique": "MZ",
        "Myanmar": "MM",
        "Namibia": "NA",
        "Nauru": "NR",
        "Nepal": "NP",
        "Netherlands": "NL",
        "New Zealand": "NZ",
        "Nicaragua": "NI",
        "Niger": "NE",
        "Nigeria": "NG",
        "North Macedonia": "MK",
        "Norway": "NO",
        "Oman": "OM",
        "Pakistan": "PK",
        "Palau": "PW",
        "Palestine": "PS",
        "Panama": "PA",
        "Papua New Guinea": "PG",
        "Paraguay": "PY",
        "Peru": "PE",
        "Philippines": "PH",
        "Portugal": "PT",
        "Qatar": "QA",
        "Romania": "RO",
        "Russia": "RU",
        "Rwanda": "RW",
        "Saint Kitts and Nevis": "KN",
        "Saint Lucia": "LC",
        "Saint Vincent and the Grenadines": "VC",
        "Samoa": "WS",
        "San Marino": "SM",
        "Sao Tome and Principe": "ST",
        "Saudi Arabia": "SA",
        "Senegal": "SN",
        "Serbia": "RS",
        "Seychelles": "SC",
        "Sierra Leone": "SL",
        "Singapore": "SG",
        "Slovakia": "SK",
        "Slovenia": "SI",
        "Solomon Islands": "SB",
        "Somalia": "SO",
        "South Africa": "ZA",
        "South Sudan": "SS",
        "Sri Lanka": "LK",
        "Sudan": "SD",
        "Suriname": "SR",
        "Sweden": "SE",
        "Switzerland": "CH",
        "Syria": "SY",
        "Taiwan": "TW",
        "Tajikistan": "TJ",
        "Tanzania": "TZ",
        "Thailand": "TH",
        "Timor-Leste": "TL",
        "Togo": "TG",
        "Tonga": "TO",
        "Trinidad and Tobago": "TT",
        "Tunisia": "TN",
        "Turkey": "TR",
        "Turkmenistan": "TM",
        "Tuvalu": "TV",
        "Uganda": "UG",
        "Ukraine": "UA",
        "United Arab Emirates": "AE",
        "United States": "US",
        "Uruguay": "UY",
        "Uzbekistan": "UZ",
        "Vanuatu": "VU",
        "Vatican City": "VA",
        "Venezuela": "VE",
        "Vietnam": "VN",
        "Yemen": "YE",
        "Zambia": "ZM",
        "Zimbabwe": "ZW"
    }.get(country_name, "PL")

def build_items(lines):
    items = []
    for line in lines:
        sku = line.get("SKU", line.get("Sku", ""))
        if sku == "" or line.get("ProductID") == "00000000-0000-0000-0000-000000000000":
            continue
        items.append({
            "sku": sku,
            "externalId": line["ProductID"],
            "ordered": line["Quantity"],
            "quantity": line["Quantity"],
            "description": line["Name"],
            "weight": float(line.get("ProductWeight", 0.1)),
            "vat_code": 23,
            "price_gross": float(line["Price"]),
            "price_net": float(line["Total"])
        })
    return items

def build_payload_from_core(data):
    order_data = data["Order"]
    shipping = data.get("ShippingAddress", {})
    clientOrderNumber = order_data["SaleOrderNumber"]
    orderDate = data.get("SaleOrderDate", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    deliveryRecipient = data.get("Customer", "Unknown Customer")
    deliveryEmail = data.get("Email", "test@example.com")
    deliveryStreet = shipping.get("Line1", "Test Street 10")
    deliveryPostCode = shipping.get("Postcode", "00-001")
    deliveryCity = shipping.get("City", "Warszawa")
    deliveryCountry = get_country_code(shipping.get("Country", "Poland"))

    # Determine base country flag for carrier/delivery point logic
    is_poland = shipping.get("Country") == "Poland"
    carrier = "Kurier InPost - ShipX" if is_poland else "FedEx"
    deliveryPointId = (shipping.get("ID") or "KKZ01A") if is_poland else None
    depotId = "556239"

    # --- Currency Determination Logic (Corrected) ---
    # 1. Try to get currency directly from the order data
    currency = order_data.get("SaleOrderCurrency") or order_data.get("Currency")

    # 2. If not found in order data, determine fallback based on country
    if not currency: # Only if it was genuinely missing from the API response
        country_name = shipping.get("Country")
        if country_name == "Poland":
            currency = "PLN"
        elif country_name == "Sweden": # This will now be checked
            currency = "SEK"
        elif country_name == "United Kingdom":
            currency = "GBP"
        else:
            # Default to EUR for other countries if currency isn't specified in API
            currency = "EUR"
    # --- End Currency Determination Logic ---

    phone = data.get("Phone", "") or shipping.get("Phone", "")
    if not phone:
        phone = "+4401403740350"

    items = build_items(order_data["Lines"])
    priceGross = sum(item['price_gross'] for item in items)

    return {
        "clientOrderNumber": clientOrderNumber,
        "externalId": clientOrderNumber,
        "paymentMethod": currency,
        "currencySymbol": currency,
        "orderDate": orderDate,
        "carrier": carrier,
        "deliveryRecipient": deliveryRecipient,
        "deliveryPhone": phone,
        "deliveryEmail": deliveryEmail,
        "deliveryStreet": deliveryStreet,
        "deliveryPostCode": deliveryPostCode,
        "deliveryCity": deliveryCity,
        "deliveryCountry": deliveryCountry,
        "deliveryPointId": deliveryPointId,
        "depotId": depotId,
        "shipmentPrice": 0.00,
        "priceGross": priceGross,
        "items": items,
        "comments": "Created from test.py with Core SaleID"
    }

def send_to_inpost(payload):
    url = f"https://api-inpost.linker.shop/public-api/v1/orders?apikey={INPOST_API_KEY}"
    response = requests.post(url, headers=inpost_headers, json=payload)
    print(f"📦 Sent to InPost: {payload['externalId']} | Status: {response.status_code}")
    
    if response.status_code == 409:
        print("ℹ️  Order already exists in InPost (duplicate), continuing...")
        return response
    
    return response

def get_inpost_order_by_external_id(order_id):
    url = f"https://api-inpost.linker.shop/public-api/v1/orders?apikey={INPOST_API_KEY}&filters[external_id]={order_id}"
    response = requests.get(url)
    return response.json().get("items", [])

def get_inpost_order_by_id(order_id):
    """Get InPost order by internal ID"""
    url = f"https://api-inpost.linker.shop/public-api/v1/orders/{order_id}?apikey={INPOST_API_KEY}"
    try:
        response = requests.get(url, headers=inpost_headers)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

def cancel_order_in_inpost(inpost_order_id):
    """Cancel an order in InPost by updating its status to 'A'"""
    base_url = f"https://api-inpost.linker.shop/public-api/v1/orders"
    api_key_param = f"apikey={INPOST_API_KEY}"
    
    print(f"📥 Fetching order details for {inpost_order_id}...")
    get_url = f"{base_url}/{inpost_order_id}?{api_key_param}"
    
    try:
        get_response = requests.get(get_url, headers=inpost_headers)
        if get_response.status_code != 200:
            print(f"❌ Failed to fetch order {inpost_order_id}: {get_response.status_code} - {get_response.text}")
            return False
            
        order_data = get_response.json()
        print(f"✅ Successfully fetched order details")
        
    except Exception as e:
        print(f"❌ Error fetching order {inpost_order_id}: {str(e)}")
        return False
    
    order_data["orderStatus"] = "A"
    
    fields_to_remove = ["id", "uuid", "createdAt", "updatedAt", "statusHistory", 
                       "externalDeliveryIds", "number", "wms_id", "origin"]
    for field in fields_to_remove:
        order_data.pop(field, None)
    
    put_url = f"{base_url}/{inpost_order_id}?{api_key_param}"
    print(f"📤 Updating order status to 'A' for order {inpost_order_id}...")
    
    try:
        put_response = requests.put(put_url, headers=inpost_headers, json=order_data)
        if put_response.status_code in [200, 204]:
            print(f"✅ Order {inpost_order_id} status updated to 'A' (cancelled) in InPost")
            return True
        else:
            print(f"❌ Failed to update order {inpost_order_id} status: {put_response.status_code} - {put_response.text}")
            if put_response.status_code == 400:
                try:
                    error_details = put_response.json()
                    print(f"📝 Validation errors: {json.dumps(error_details, indent=2)}")
                except:
                    pass
            return False
    except Exception as e:
        print(f"❌ Error updating order {inpost_order_id} status: {str(e)}")
        return False

def check_and_sync_cancelled_orders():
    """Check for orders cancelled in CIN7 and cancel them in InPost"""
    print("🔍 Checking for cancelled orders that need to be synced to InPost...")
    
    cancelled_orders = get_recent_voided_orders(7)
    
    for order in cancelled_orders:
        order_number = order.get("OrderNumber", "")
        sale_id = order.get("SaleID", "")
        
        if not order_number:
            continue
            
        print(f"📋 Checking cancelled order: {order_number}")
        
        inpost_orders = get_inpost_order_by_external_id(order_number)
        if inpost_orders:
            inpost_order_id = inpost_orders[0].get("id")
            if inpost_order_id:
                if cancel_order_in_inpost(inpost_order_id):
                    print(f"✅ Successfully synced cancellation for order {order_number}")
                else:
                    print(f"❌ Failed to cancel order {order_number} in InPost")
            else:
                print(f"⚠️  No InPost order ID found for {order_number}")
        else:
            print(f"✅ Order {order_number} not found in InPost (already cancelled or never sent)")

def get_recent_voided_orders(days_back=7):
    """Get recently voided orders from CIN7"""
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    
    url = f"https://inventory.dearsystems.com/ExternalApi/v2/saleList?From={start_date}&Status=Voided&Limit=1000"
    
    try:
        response = dear_request("GET", url, headers=core_headers)
        data = response.json()

        if not data.get("SaleList"):
            print("ℹ️  No recently voided orders found.")
            return []

        voided_orders = data["SaleList"]
        print(f"📥 Found {len(voided_orders)} recently voided orders in CIN7 (since {start_date})")
        return voided_orders
    except Exception as e:
        print(f"❌ Error fetching voided orders: {str(e)}")
        return []

def check_actual_fulfillment_status(data, sale_id):
    """Check actual fulfillment status from the fulfillment API and return fulfillment task ID and pack box info."""
    print(f"🔍 Checking fulfillment status for SaleID: {sale_id}")
    fulfillment_data = get_fulfillment_status(sale_id)
    
    pick_done = False
    pack_done = False
    ship_done = False
    fulfillment_task_id = None
    pack_box_name = "1"
    packed_lines = []
    raw_pack_lines_from_core = [] # Add this variable to capture the raw data
    
    if fulfillment_data and "Fulfilments" in fulfillment_data and fulfillment_data["Fulfilments"]:
        fulfillment = fulfillment_data["Fulfilments"][0]
        fulfillment_task_id = fulfillment.get("TaskID")
        fulfillment_number = fulfillment.get("FulfillmentNumber", "Unknown")
        
        print(f"📋 Processing fulfillment: {fulfillment_number} (TaskID: {fulfillment_task_id})")
        
        if "Pick" in fulfillment and fulfillment["Pick"]:
            pick_status = fulfillment["Pick"].get("Status", "")
            pick_done = pick_status in ["AUTHORISED", "PICKED", "COMPLETED"]
            print(f"  📦 Pick Status: {pick_status} ({'✅ Done' if pick_done else '❌ Not Done'})")
        
        if "Pack" in fulfillment and fulfillment["Pack"]:
            pack_status = fulfillment["Pack"].get("Status", "")
            pack_done = pack_status in ["AUTHORISED", "PACKED", "COMPLETED"]
            print(f"  📦 Pack Status: {pack_status} ({'✅ Done' if pack_done else '❌ Not Done'})")
            
            if "Lines" in fulfillment["Pack"] and fulfillment["Pack"]["Lines"]:
                first_pack_line = fulfillment["Pack"]["Lines"][0]
                pack_box_name = first_pack_line.get("Box", "1")
                print(f"  📦 Pack Box Name: {pack_box_name}")
                
                raw_pack_lines_from_core = fulfillment["Pack"]["Lines"] # Store the raw lines
                
                for pl in fulfillment["Pack"]["Lines"]:
                    # Determine the packed quantity field reliably
                    qty = (
                        pl.get("Packed")
                        or pl.get("PackedQuantity")
                        or pl.get("QuantityPacked")
                        or pl.get("Quantity")
                        or 0
                    )
                    try:
                        qty = float(qty)
                    except Exception:
                        qty = 0
                    if qty and qty > 0:
                        packed_line = {
                            "ProductID": pl.get("ProductID"),
                            "SKU": pl.get("SKU"),
                            "Name": pl.get("Name"),
                            "Location": pl.get("Location"), # Copy Location from raw data
                            "LocationID": pl.get("LocationID"), # Copy LocationID from raw data
                            "Quantity": qty,
                            "Box": pl.get("Box", pack_box_name)
                        }
                        packed_lines.append(packed_line)
                        
        if "Ship" in fulfillment and fulfillment["Ship"]:
            ship_status = fulfillment["Ship"].get("Status", "")
            ship_done = ship_status in ["AUTHORISED", "SHIPPED", "COMPLETED"]
            print(f"  📦 Ship Status: {ship_status} ({'✅ Done' if ship_done else '❌ Not Done'})")
    else:
        print("⚠️  No fulfillment data found or empty fulfillment list")
    
    print(f"📊 Final status - PICK: {'✅' if pick_done else '❌'}, PACK: {'✅' if pack_done else '❌'}, SHIP: {'✅' if ship_done else '❌'}")
    
    # Log the raw pack lines for debugging
    print(f"📦 Raw Pack Lines from Core API: {json.dumps(raw_pack_lines_from_core, indent=2)}")
    
    return pick_done, pack_done, ship_done, fulfillment_task_id, pack_box_name, packed_lines, raw_pack_lines_from_core # Return the raw lines


def check_if_fulfillment_exists(task_id, fulfillment_type):
    """Check if fulfillment already exists for this task."""
    url = f"https://inventory.dearsystems.com/ExternalApi/v2/sale/fulfilment/{fulfillment_type}?TaskID={task_id}"
    try:
        response = dear_request("GET", url, headers=core_headers)
        if response.status_code == 200:
            data = response.json()
            return len(data) > 0
        return False
    except Exception as e:
        print(f"❌ Error checking fulfillment existence: {str(e)}")
        return False

def attempt_authorize_pick(task_id, lines):
    """Attempt to authorize picking for an order."""
    url = "https://inventory.dearsystems.com/ExternalApi/v2/sale/fulfilment/pick"
    payload = {
        "TaskID": task_id,
        "Status": "AUTHORISED",
        "Lines": lines
    }
    
    try:
        response = dear_request("POST", url, headers=core_headers, json=payload)
        print(f"📥 PICK response: {response.status_code}")
        if response.status_code == 200:
            print(f"✅ PICK AUTHORIZED | HTTP {response.status_code}")
            return True, True
        elif response.status_code == 400:
            error_text = response.text.lower()
            if "already" in error_text or "exists" in error_text:
                print("✅ PICK already authorized")
                return True, True
            else:
                print(f"⚠️  PICK authorization issues: {response.text}")
                return True, False
        else:
            response.raise_for_status()
            return True, True
    except Exception as e:
        print(f"❌ Error authorizing pick for task {task_id}: {str(e)}")
        return False, False

def attempt_authorize_pack(task_id, lines):
    """Attempt to authorize packing for an order."""
    url = "https://inventory.dearsystems.com/ExternalApi/v2/sale/fulfilment/pack"
    payload = {
        "TaskID": task_id,
        "Status": "AUTHORISED",
        "Lines": lines
    }
    
    try:
        response = dear_request("POST", url, headers=core_headers, json=payload)
        print(f"📥 PACK response: {response.status_code}")
        if response.status_code == 200:
            print(f"✅ PACK AUTHORIZED | HTTP {response.status_code}")
            return True, True
        elif response.status_code == 400:
            error_text = response.text.lower()
            if "already" in error_text or "exists" in error_text:
                print("✅ PACK already authorized")
                return True, True
            else:
                print(f"⚠️  PACK authorization issues: {response.text}")
                return True, False
        else:
            response.raise_for_status()
            return True, True
    except Exception as e:
        print(f"❌ Error authorizing pack for task {task_id}: {str(e)}")
        return False, False

# === CRITICAL NEW HELPER FUNCTION FOR MERGING AND CLEANING SHIP LINES ===
def _merge_and_clean_ship_lines(original_order_lines, raw_packed_lines):
    """
    Merges original order lines (for SaleLineID) with raw packed lines (for LocationID),
    and strips the line item down to the minimalist fields required for SHIP authorization.
    """
    
    # 1. Create a map of original lines for quick lookup by ProductID
    original_line_map = {}
    
    # DEBUG: Log the input to confirm the fix works
    print(f"DEBUG: Starting SaleLineID merge. Original order line count: {len(original_order_lines)}")

    for line in original_order_lines:
        prod_id = line.get("ProductID")
        sale_line_id = line.get("SaleLineID") # Safely get the ID
        
        # Check 1: Must have a valid ProductID
        if not prod_id or prod_id == "00000000-0000-0000-0000-000000000000":
            continue
            
        # Check 2: Must have a valid SaleLineID 
        if not sale_line_id or sale_line_id == "00000000-0000-0000-0000-000000000000":
            # This is the line that was being triggered previously
            continue
            
        if prod_id not in original_line_map:
            original_line_map[prod_id] = []
        
        # Store the essential data for merging
        original_line_map[prod_id].append({
            "SaleLineID": sale_line_id,
            "Quantity": float(line.get("Quantity", 0) or 0),
            "consumed_qty": 0.0 # Track how much of this original line has been fulfilled
        })

    if not original_line_map:
        print("❌ SHIP preparation failed: The original_line_map is empty. SaleLineID is still missing from ALL required order lines.")
        return []

    final_ship_lines = []
    
    # 2. Iterate through the packed lines and merge data
    for packed_line in raw_packed_lines:
        prod_id = packed_line.get("ProductID")
        packed_qty = float(packed_line.get("Quantity", 0) or 0)
        location_id = packed_line.get("LocationID")
        
        if not prod_id or not location_id or packed_qty <= 0:
            continue
            
        if prod_id in original_line_map:
            # Find an original line item to assign this packed quantity to
            for original_line in original_line_map[prod_id]:
                remaining_qty = original_line["Quantity"] - original_line["consumed_qty"]
                
                # If there's quantity left to assign on this original line
                if remaining_qty > 0:
                    # Quantity to ship for this SaleLineID is the minimum of
                    # the packed quantity and the remaining quantity on the original line
                    qty_to_ship = min(packed_qty, remaining_qty)
                    
                    if qty_to_ship > 0:
                        final_ship_lines.append({
                            "SaleLineID": original_line["SaleLineID"], # <-- CRITICAL FIX: SALE LINE ID
                            "ProductID": prod_id,
                            "Quantity": qty_to_ship,
                            "LocationID": location_id # <-- REQUIRED FIX: LOCATION ID
                            # Minimalist fields only
                        })
                        
                        # Update consumed quantities for tracking
                        original_line["consumed_qty"] += qty_to_ship
                        packed_qty -= qty_to_ship # Reduce remaining packed quantity to assign
                        
                        if packed_qty <= 0:
                            break # All of this packed line is assigned
        # else: debug log removed

    if not final_ship_lines:
        print("❌ SHIP preparation failed: Could not merge SaleLineID with packed lines (final list is empty).")

    return final_ship_lines
# === END NEW HELPER FUNCTION ===



def authorize_ship(
    task_id,
    tracking_number,
    tracking_url,
    shipping_address,
    lines,
    box_name,
    carrier,
    raw_pack_lines_from_core=None,
    original_order_lines=None,
):
    """
    Authorize shipping for an order.

    This mirrors the legacy PHP behaviour:
      - POST /ExternalApi/v2/sale/fulfilment/ship
      - Shipment-level only (no item lines, no SaleLineID)
      - Single box "Box 1"
      - Uses ShipBy and Carrier from Core
    """
    url = "https://inventory.dearsystems.com/ExternalApi/v2/sale/fulfilment/ship"

    # ShipBy and Carrier should come from the sale root; we pass them via
    # the shipping_address dict before calling this function.
    ship_by = shipping_address.get("ShipBy")
    core_carrier = shipping_address.get("Carrier") or carrier

    # Fallback for ShipmentDate if ShipBy is missing
    if ship_by:
        # Core uses full datetime; we can safely pass date part or full string
        shipment_date = ship_by
    else:
        shipment_date = datetime.now().strftime("%Y-%m-%d")

    shipment_line = {
        "ShipmentDate": shipment_date,
        "Carrier": core_carrier,
        # IMPORTANT: PHP sends literal "Box 1"
        "Box": "Box 1",
        "TrackingNumber": tracking_number,
        "TrackingURL": tracking_url or "",
        "IsShipped": True,
    }

    payload = {
        "TaskID": task_id,
        "Status": "AUTHORISED",
        # PHP sends null RequireBy
        "RequireBy": None,
        "ShippingAddress": {
            "DisplayAddressLine1": shipping_address.get("DisplayAddressLine1", ""),
            "DisplayAddressLine2": shipping_address.get("DisplayAddressLine2", ""),
            "Line1": shipping_address.get("Line1", ""),
            "Line2": shipping_address.get("Line2", ""),
            "City": shipping_address.get("City", ""),
            "State": shipping_address.get("State", ""),
            "Postcode": shipping_address.get("Postcode", ""),
            "Country": shipping_address.get("Country", ""),
            "Company": shipping_address.get("Company", ""),
            "Contact": shipping_address.get("Contact", ""),
            "ShipToOther": shipping_address.get("ShipToOther", False),
        },
        # Exactly like PHP: use ShippingNotes from Core if present
        "ShippingNotes": shipping_address.get("ShippingNotes", ""),
        "Lines": [shipment_line],
    }

    print(f"📤 SHIP payload (PHP-style): {json.dumps(payload, indent=2)}")

    try:
        response = dear_request("POST", url, headers=core_headers, json=payload)
        print(f"📥 SHIP response: {response.status_code} - {response.text}")
        if response.status_code == 200:
            print(f"✅ SHIP AUTHORIZED | HTTP {response.status_code}")
            return True
        elif response.status_code == 400:
            error_text = response.text.lower()
            if "already" in error_text or "exists" in error_text:
                print("✅ SHIP already authorized")
                return True
            else:
                print(f"❌ SHIP authorization failed: {response.text}")
                try:
                    error_details = response.json()
                    print(f"📝 Detailed Error: {json.dumps(error_details, indent=2)}")
                except Exception:
                    pass
                return False
        else:
            print(f"❌ Unexpected SHIP status: {response.status_code} - {response.text}")
            return False
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error authorizing ship for task {task_id}: {e}")
        return False
    except Exception as e:
        print(f"❌ Error authorizing ship for task {task_id}: {str(e)}")
        return False


def process_fulfillment(data, sale_id, tracking_number, tracking_url):
    """Process all fulfillment steps (PICK, PACK, SHIP) for an order."""
    order_data = data["Order"]
    sale_task_id = data["ID"]
    lines = order_data.get("Lines", []) # Get original order lines (contains SaleLineID, hopefully now)
    shipping = data.get("ShippingAddress", {})
    
    # Unpack the new return value
    pick_done, pack_done, ship_done, fulfillment_task_id, pack_box_name, packed_lines_from_core, raw_pack_lines_from_core = check_actual_fulfillment_status(data, sale_id)
    
    task_id_to_use = fulfillment_task_id if fulfillment_task_id else sale_task_id
    print(f"🔧 Using Task ID for fulfillment: {task_id_to_use}")
    print(f"📦 Using Box Name: {pack_box_name}")
    
    fulfillment_lines = []
    for line in lines:
        if line.get("SKU") and line.get("ProductID") != "00000000-0000-0000-0000-000000000000":
            fulfillment_lines.append({
                "ProductID": line["ProductID"],
                "SKU": line["SKU"],
                "Name": line["Name"],
                "Location": "InPost",
                "Quantity": line["Quantity"]
            })
    
    pack_lines = []
    for line in fulfillment_lines:
        pack_line = line.copy()
        pack_line["Box"] = pack_box_name
        pack_lines.append(pack_line)
    
    success = True
    pick_success = True
    pack_success = True
    
    if not pick_done:
        print("🔄 Attempting PICK authorization...")
        pick_ok, pick_clean = attempt_authorize_pick(task_id_to_use, fulfillment_lines)
        if not pick_ok:
            print("❌ PICK authorization failed completely")
            pick_success = False
            success = False
        elif not pick_clean:
            print("⚠️  PICK has inventory issues but continuing...")
        else:
            print("✅ PICK authorization successful")
    else:
        print("✅ PICK already authorized, skipping...")
        pick_success = True
    
    if not pack_done:
        if pick_success or pick_done:
            print("🔄 Attempting PACK authorization...")
            pack_ok, pack_clean = attempt_authorize_pack(task_id_to_use, pack_lines)
            if not pack_ok:
                print("❌ PACK authorization failed completely")
                pack_success = False
                success = False
            elif not pack_clean:
                print("⚠️  PACK has issues but continuing...")
            else:
                print("✅ PACK authorization successful")
        else:
            print("⏭️  Skipping PACK due to PICK failure")
            pack_success = False
            success = False
    else:
        print("✅ PACK already authorized, skipping...")
        pack_success = True
    
    # Choose the lines to use for SHIP: prefer exact packed lines from Core if available
    # NOTE: ship_lines here is ONLY used for pre-flight log, not the payload construction
    ship_lines = packed_lines_from_core if packed_lines_from_core else pack_lines
    
    # Pre-flight log: compare order lines vs ship lines and print ship lines for debugging
    try:
        ordered_qty = sum(float(l.get("Quantity", 0) or 0) for l in fulfillment_lines)
        ship_qty = sum(float(l.get("Quantity", 0) or 0) for l in ship_lines)
        print(f"🧮 Line check: ordered (fulfillment) qty={ordered_qty}, ship qty={ship_qty}, items: ordered={len(fulfillment_lines)}, ship={len(ship_lines)}")
        print(f"🧾 Ship lines detail: {json.dumps(ship_lines, indent=2)}")
        missing = []
        order_key = lambda l: (l.get("ProductID"), str(l.get("Box", pack_box_name)))
        ship_map = {}
        for l in ship_lines:
            key = order_key(l)
            ship_map[key] = ship_map.get(key, 0) + float(l.get("Quantity", 0) or 0)
        for l in pack_lines:
            key = order_key(l)
            q = float(l.get("Quantity", 0) or 0)
            if ship_map.get(key, 0) < q:
                missing.append({"ProductID": l.get("ProductID"), "SKU": l.get("SKU"), "need": q, "have": ship_map.get(key, 0), "Box": l.get("Box", pack_box_name)})
        if missing:
            print(f"⚠️  Potential missing lines for SHIP: {json.dumps(missing, indent=2)}")
    except Exception as e:
        print(f"⚠️  Pre-flight line check failed: {str(e)}")
    
    # Compute appropriate carrier (align with Dear): FedEx for non-Poland, InPost for Poland
    country = (shipping or {}).get("Country", "")
    computed_carrier = "Kurier InPost - ShipX" if country == "Poland" else "FedEx"
    
    
    if (pick_done or pick_success) and (pack_done or pack_success):
        print("🔄 Attempting SHIP authorization...")
        # Small delay to let Dear/Cin7 internal state settle
        print("⏳ Waiting 2 seconds before attempting SHIP authorization...")
        time.sleep(2)

        # We no longer try to send item-level lines for SHIP – Dear only needs
        # shipment-level info here. Item quantities are governed by PACK.

        # shipping is your ShippingAddress dict from Core
        shipping["ShipBy"] = data.get("ShipBy")
        shipping["Carrier"] = data.get("Raw", {}).get("Carrier")
        shipping["ShippingNotes"] = data.get("Raw", {}).get("ShippingNotes", "")

        if not authorize_ship(
            task_id_to_use,
            tracking_number,
            tracking_url,
            shipping,
            [],  # item lines not required for SHIP
            pack_box_name,
            computed_carrier,
            raw_pack_lines_from_core,
            lines,
        ):
            print("❌ SHIP authorization failed")
            success = False
        else:
            print("✅ SHIP authorization successful")
    else:
        print("⏭️  Skipping SHIP due to PICK/PACK not being ready")
        success = False


        return success


def get_recent_sale_ids(days_back=1):
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    url = f"https://inventory.dearsystems.com/ExternalApi/v2/saleList?From={start_date}&Limit=1000"
    
    try:
        response = dear_request("GET", url, headers=core_headers)
        data = response.json()

        if not data.get("SaleList"):
            print("❌ No sales found.")
            return []
        
        # Filter for multiple relevant statuses to include B2B orders
        relevant_statuses = ["ORDERED", "AUTHORISED", "INVOICED"]
        
        return [sale["SaleID"] for sale in data["SaleList"] if sale.get("Status") in relevant_statuses]
    except Exception as e:
        print(f"❌ Error fetching recent sales: {str(e)}")
        return []


def update_tracking_in_core(sale_id, tracking_number, tracking_url):
    """Update tracking information in Core (mirror legacy PHP).

    PHP calls:
      PUT /ExternalApi/v2/sale/{SaleID}/fulfilment/ship
      Body: { "trackingNumber": "...", "trackingURL": "..." }
    """
    url = f"https://inventory.dearsystems.com/ExternalApi/v2/sale/{sale_id}/fulfilment/ship"

    payload = {
        "trackingNumber": tracking_number,
        "trackingURL": tracking_url or "",
    }

    print(f"📤 Updating tracking in Core via: {url}")
    print(f"📤 Tracking payload: {json.dumps(payload, indent=2)}")

    try:
        response = dear_request("PUT", url, headers=core_headers, json=payload)
        if response.status_code == 200:
            print(f"✅ Successfully updated tracking in Core: {tracking_number}")
            return True
        else:
            print(
                f"❌ Failed to update tracking in Core: "
                f"{response.status_code} - {response.text}"
            )
            try:
                error_details = response.json()
                print(f"📝 Tracking update error details: {json.dumps(error_details, indent=2)}")
            except Exception:
                pass
            return False
    except Exception as e:
        print(f"❌ Error updating tracking in Core: {str(e)}")
        return False


def validate_order_for_inpost(data):

    """Validate order data before sending to InPost"""
    order_data = data["Order"]
    shipping = data.get("ShippingAddress", {})
    
    errors = []
    
    country = shipping.get("Country", "")
    is_poland = country == "Poland"
    
    delivery_point = shipping.get("ID", "")
    if is_poland and not delivery_point:
        errors.append("❌ Polish shipments require a delivery point ID")
    elif not is_poland and delivery_point:
        errors.append("❌ Non-Polish shipments should not have a delivery point ID")
    
    email = data.get("Email", "") or shipping.get("Email", "") or "organic@greenpeople.co.uk"
    
    if country == "Sweden" and shipping.get("Postcode", "").startswith("52-"):
        errors.append("❌ Country is Sweden but Polish postcode format detected")
    
    return errors

# === MAIN ===

check_and_sync_cancelled_orders()

SALE_IDS = get_recent_sale_ids(1)

for sale_id in SALE_IDS:
    data = get_core_sale(sale_id)
    
    # CRITICAL FIX 1: Stop immediately if data fetching failed
    if not data or "Order" not in data:
        print(f"❌ Failed to retrieve valid data for sale {sale_id}")
        continue
        
    order_data = data["Order"]
    
    # 🔥 FINAL FIX: Safely retrieve SaleOrderNumber. Default to "" if missing.
    order_number = order_data.get("SaleOrderNumber", "") 
    
    if not order_number:
        print(f"❌ Sale Order Number not found in Core data for sale {sale_id}. Skipping.")
        continue
    
    task_id = data["ID"]
    lines = order_data.get("Lines", []) # Use order_data directly
    
    # CRITICAL FIX 2: Safely access ShippingAddress. It should be a dict if the function above worked.
    shipping = data.get("ShippingAddress", {}) or {} 
    
    # Use .get("Country") on the safe shipping dictionary
    country = shipping.get("Country", "") 
    carrier = "Kurier InPost - ShipX" if country == "Poland" else "FedEx"
    ship_by = data.get("ShipBy", "")

    print(f"\n🔄 Processing Core Sale: {order_number}")
    print(f"📋 Task ID: {task_id}")

    validation_errors = validate_order_for_inpost(data)
    if validation_errors:
        print(f"❌ Order {order_number} has validation errors:")
        for error in validation_errors:
            print(f"   {error}")
        print("⏭️  Skipping order due to validation errors")
        continue

    payload = build_payload_from_core(data)
    response = send_to_inpost(payload)
    
    if response.status_code not in [200, 201, 409]:
        print(f"❌ Failed to send to InPost, skipping order {order_number}")
        continue

    print(f"🔍 Checking InPost status for {order_number}...")
    inpost_order = get_inpost_order_by_external_id(order_number)
    if not inpost_order:
        print("❌ InPost order not found, skipping...")
        continue
        
    order_status = inpost_order[0].get("orderStatus")
    if order_status != "Y":
        print(f"❌ Not ready (InPost order status: {order_status}), skipping...")
        continue

    print("✅ InPost marked as sent. Proceeding to complete in Core...")

    # Get tracking info with better error handling
    inpost_order_data = inpost_order[0] if inpost_order else {}
    external_delivery = inpost_order_data.get("externalDeliveryIds", [{}])
    operators_data = external_delivery[0].get("operators_data", [{}]) if external_delivery else [{}]
    tracking_info = operators_data[0] if operators_data else {}

    tracking_number = tracking_info.get("package_id", "")
    tracking_url = tracking_info.get("tracking_url", "")

    if not tracking_number:
        print("❌ No tracking number available, skipping fulfillment...")
        continue
        
    # Update tracking information in Core
    if not update_tracking_in_core(sale_id, tracking_number, tracking_url):
        print("❌ Failed to update tracking in Core, but continuing with fulfillment...")

    print("🔄 Processing fulfillment authorization...")
    if process_fulfillment(data, sale_id, tracking_number, tracking_url):
        print(f"✅ Successfully completed all fulfillment steps for order {order_number}")
    else:
        print(f"⚠️  Some fulfillment steps may have failed for order {order_number}")

    print(f"✅ Completed processing for order: {order_number}")