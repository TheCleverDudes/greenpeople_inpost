import requests
import json
from datetime import datetime

# === Cin7 Core (DEAR) API credentials ===
CORE_ACCOUNT_ID = "3384f900-b8b1-41bc-8324-1e6000e897ec"
CORE_APP_KEY = "c1bf7dbf-5365-9d50-95a1-960ee4455445"

# === InPost API key ===
INPOST_API_KEY = "da3f39f46c9f473d29cc8ec40a0ae787"

# === Replace with a valid SaleID ===
SALE_ID = "9b15e51a-d1d2-4c03-8c4b-4f070a3dd41e"

# === Step 1: Fetch sale order from Core ===
core_url = f"https://inventory.dearsystems.com/ExternalApi/v2/sale?ID={SALE_ID}&CombineAdditionalCharges=true"
core_headers = {
    "Content-Type": "application/json",
    "api-auth-accountid": CORE_ACCOUNT_ID,
    "api-auth-applicationkey": CORE_APP_KEY
}

core_response = requests.get(core_url, headers=core_headers)
data = core_response.json()

# === Step 2: Validate expected fields ===
if "Order" not in data or "Lines" not in data["Order"]:
    print("❌ Error: Unexpected API response")
    print(json.dumps(data, indent=4))
    exit()

# === Extract fields ===
order_data = data["Order"]
shipping = data.get("ShippingAddress", {})

def get_country_code(country_name):
    country_codes = {
        "Poland": "PL",
        "Poland": "PL",  # Added again for case where it might be "Poland"
        "Germany": "DE",
        "France": "FR",
        "United Kingdom": "GB",
        "Ireland": "IE",
        "Italy": "IT",
        "Spain": "ES",
        "Netherlands": "NL",
        "Belgium": "BE",
        "Luxembourg": "LU"
    }
    return country_codes.get(country_name, "PL")  # Default to PL if not found

clientOrderNumber = order_data["SaleOrderNumber"]
orderDate = data.get("SaleOrderDate", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
deliveryRecipient = data.get("Customer", "Unknown Customer")
deliveryEmail = data.get("Email", "test@example.com")
deliveryStreet = shipping.get("Line1", "Test Street 10")
deliveryPostCode = shipping.get("Postcode", "00-001")
deliveryCity = shipping.get("City", "Warszawa")
deliveryCountry = get_country_code(shipping.get("Country", "Poland"))

# Determine carrier and delivery details based on country
is_poland = shipping.get("Country") == "Poland"
carrier = "Kurier InPost - ShipX" if is_poland else "FedEx"

# Only set deliveryPointId for non-courier deliveries (not for InPost courier)
deliveryPointId = None if is_poland else (shipping.get("ID") or "KKZ01A")
depotId = "556239"

# Try to get the original currency from order data, fallback to PLN/EUR based on country
currency = order_data.get("SaleOrderCurrency") or order_data.get("Currency") or ("PLN" if is_poland else "EUR")

# Handle phone number
phone = data.get("Phone", "")
if not phone:
    phone = "+48500600700" if is_poland else "+441403740350"  # Default numbers if none provided

# === Step 3: Build items ===
items = []
for line in order_data["Lines"]:
    sku = line.get("SKU", line.get("Sku", ""))
    if sku == "" or line.get("ProductID") == "00000000-0000-0000-0000-000000000000":
        continue  # skip placeholder shipping lines

    items.append({
        "sku": sku,
        "externalId": line["ProductID"],
        "ordered": line["Quantity"],
        "quantity": line["Quantity"],
        "description": line["Name"],
        "weight": float(line.get("ProductWeight", 0.1)) / 1000,  # convert g to kg
        "vat_code": 23,
        "price_gross": float(line["Price"]),
        "price_net": float(line["Total"])
    })

# === Step 4: Calculate totals ===
priceGross = sum(item['price_gross'] for item in items)

# === Step 5: Build InPost payload ===
inpost_payload = {
    "clientOrderNumber": clientOrderNumber,
    "externalId": clientOrderNumber,
    "paymentMethod": currency,  # Use dynamic currency
    "currencySymbol": currency,  # Use dynamic currency
    "orderDate": orderDate,
    "carrier": carrier,  # Dynamic carrier
    "deliveryRecipient": deliveryRecipient,
    "deliveryPhone": phone,  # Use processed phone number
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

# === Step 6: Send to InPost ===
inpost_url = f"https://api-inpost.linker.shop/public-api/v1/orders?apikey={INPOST_API_KEY}"
headers = {"Content-Type": "application/json"}

print(f"🔄 Creating SO {clientOrderNumber} in InPost...")
response = requests.post(inpost_url, headers=headers, json=inpost_payload)

print(f"\n✅ InPost API Response: HTTP {response.status_code}")
try:
    print(json.dumps(response.json(), indent=4))
except Exception:
    print("⚠️ Raw response:")
    print(response.text)
