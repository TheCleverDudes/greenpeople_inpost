import requests
import json
from datetime import datetime

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

def get_core_sale(sale_id):
    url = f"https://inventory.dearsystems.com/ExternalApi/v2/sale?ID={sale_id}&CombineAdditionalCharges=true"
    response = requests.get(url, headers=core_headers)
    return response.json()

def get_country_code(country_name):
    return {
        "Poland": "PL", "Germany": "DE", "France": "FR", "United Kingdom": "GB", "Ireland": "IE",
        "Italy": "IT", "Spain": "ES", "Netherlands": "NL", "Belgium": "BE", "Luxembourg": "LU"
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
            "weight": float(line.get("ProductWeight", 0.1)) / 1000,
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

    is_poland = shipping.get("Country") == "Poland"
    carrier = "Kurier InPost - ShipX" if is_poland else "FedEx"
    deliveryPointId = None if is_poland else (shipping.get("ID") or "KKZ01A")
    depotId = "556239"

    currency = order_data.get("SaleOrderCurrency") or order_data.get("Currency") or ("PLN" if is_poland else "EUR")
    phone = data.get("Phone", "+48500600700" if is_poland else "+441403740350")

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
    return response

def get_inpost_order_by_external_id(order_id):
    url = f"https://api-inpost.linker.shop/public-api/v1/orders?apikey={INPOST_API_KEY}&filters[external_id]={order_id}"
    response = requests.get(url)
    return response.json().get("items", [])

def build_fulfillment_payload(task_id, lines, shipping, carrier, ship_by, tracking_number, tracking_url):
    def base_lines(box=False):
        result = []
        for line in lines:
            if not line.get("SKU"):
                continue
            item = {
                "ProductID": line["ProductID"],
                "SKU": line["SKU"],
                "Name": line["Name"],
                "Location": "InPost",
                "Quantity": line["Quantity"]
            }
            if box:
                item["Box"] = "Box 1"
            result.append(item)
        return result

    # 👇 NEW: All shipment lines must be listed by box
    ship_lines = []
    for line in lines:
        if not line.get("SKU"):
            continue
        ship_lines.append({
            "ShipmentDate": ship_by,
            "Carrier": carrier,
            "Box": "1",  # You can dynamically name boxes if needed
            "TrackingNumber": tracking_number,
            "TrackingURL": tracking_url,
            "IsShipped": True
        })

    return {
        "pick": {
            "TaskID": task_id,
            "Status": "AUTHORISED",
            "Lines": base_lines()
        },
        "pack": {
            "TaskID": task_id,
            "Status": "AUTHORISED",
            "Lines": base_lines(box=True)
        },
        "ship": {
            "TaskID": task_id,
            "Status": "AUTHORISED",
            "RequireBy": None,
            "ShippingAddress": {
                "DisplayAddressLine1": shipping.get("DisplayAddressLine1", ""),
                "DisplayAddressLine2": shipping.get("DisplayAddressLine2", ""),
                "Line1": shipping.get("Line1", ""),
                "Line2": shipping.get("Line2", ""),
                "City": shipping.get("City", ""),
                "State": shipping.get("State", ""),
                "Postcode": shipping.get("Postcode", ""),
                "Country": shipping.get("Country", ""),
                "Company": shipping.get("Company", ""),
                "Contact": shipping.get("Contact", ""),
                "ShipToOther": shipping.get("ShipToOther", "")
            },
            "ShippingNotes": "",
            "Lines": ship_lines
        }
    }

def post_core_fulfillment(stage, payload, method="POST"):
    url = f"https://inventory.dearsystems.com/ExternalApi/v2/sale/fulfilment/{stage}"
    
    if stage == "ship" and method == "PUT":
        url += "?AddTrackingNumbers=true"
        r = requests.put(url, headers=core_headers, json=payload)
    else:
        r = requests.post(url, headers=core_headers, json=payload)

    print(f"✅ {stage.upper()} | HTTP {r.status_code}")
    try:
        print(json.dumps(r.json(), indent=2))
    except:
        print(r.text)

def get_recent_sale_ids(days_back=1):
    from datetime import timedelta

    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    url = f"https://inventory.dearsystems.com/ExternalApi/v2/saleList?From={start_date}&Limit=1000"
    
    response = requests.get(url, headers=core_headers)
    data = response.json()

    if not data.get("SaleList"):
        print("❌ No sales found.")
        return []

    return [sale["SaleID"] for sale in data["SaleList"] if sale.get("Status") == "ORDERED"]

# === MAIN ===

SALE_IDS = get_recent_sale_ids(1)

for sale_id in SALE_IDS:
    data = get_core_sale(sale_id)
    order_number = data["Order"]["SaleOrderNumber"]
    task_id = data["ID"]
    lines = data["Order"].get("Lines", [])
    shipping = data.get("ShippingAddress", {})
    carrier = data.get("Carrier", "")
    ship_by = data.get("ShipBy", "")

    print(f"\n🔄 Processing Core Sale: {order_number}")

    # Step 1: Send to InPost
    payload = build_payload_from_core(data)
    send_to_inpost(payload)

    # Step 2: Check InPost status
    print(f"🔍 Checking InPost status for {order_number}...")
    inpost_order = get_inpost_order_by_external_id(order_number)
    if not inpost_order or inpost_order[0].get("orderStatus") != "Y":
        print("❌ Not ready (InPost order not found or not in status Y)")
        continue

    print("✅ InPost marked as sent. Proceeding to complete in Core...")

    tracking_info = inpost_order[0].get("externalDeliveryIds", [{}])[0].get("operators_data", [{}])[0]
    tracking_number = tracking_info.get("package_id", "")
    tracking_url = tracking_info.get("tracking_url", "")

    fulfillment_payloads = build_fulfillment_payload(task_id, lines, shipping, carrier, ship_by, tracking_number, tracking_url)

    # Step 3: Check if PICK and PACK already authorised
    pick_status = data.get("CombinedPickingStatus", "")
    pack_status = data.get("CombinedPackingStatus", "")

    if pick_status != "PICKED":
        post_core_fulfillment("pick", fulfillment_payloads["pick"])
    else:
        print("✅ PICK already completed")

    if pack_status != "PACKED":
        post_core_fulfillment("pack", fulfillment_payloads["pack"])
    else:
        print("✅ PACK already completed")

    post_core_fulfillment("ship", fulfillment_payloads["ship"], method="PUT")
