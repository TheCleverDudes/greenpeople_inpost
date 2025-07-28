import requests
import json
from datetime import datetime, timedelta, timezone
import time
import logging
from typing import List, Dict, Optional, Tuple, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cin7_inpost_sync.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# === Configuration ===
class Config:
    # Cin7 Core (DEAR) API credentials
    CORE_ACCOUNT_ID = "3384f900-b8b1-41bc-8324-1e6000e897ec"
    CORE_APP_KEY = "c1bf7dbf-5365-9d50-95a1-960ee4455445"
    
    # InPost API key
    INPOST_API_KEY = "da3f39f46c9f473d29cc8ec40a0ae787"
    
    # Depot ID for InPost
    DEPOT_ID = "556239"
    
    # How often to check for new orders (in seconds)
    POLL_INTERVAL = 300  # 5 minutes
    
    # How far back to look for orders initially (in hours)
    INITIAL_LOOKBACK_HOURS = 72  # Increased to 72 hours
    
    # Maximum number of orders to process per batch
    MAX_BATCH_SIZE = 50
    
    # Default weights in kg
    DEFAULT_WEIGHT_KG = 0.5
    DEFAULT_ITEM_WEIGHT_KG = 0.1
    
    # Tracking URL template (if not provided by InPost)
    TRACKING_URL_TEMPLATE = "https://www.fedex.com/wtrk/track/?trknbr={}"
    
    # Default location for fulfillment
    DEFAULT_LOCATION = "InPost"
    DEFAULT_BOX = "Box 1"
    
    # Order status filter
    ORDER_STATUS_FILTER = "ALL"  # Can be "NOT FULFILLED", "FULFILLED", or "ALL"

# === Helper Functions ===
def get_country_code(country_name: str) -> str:
    """Convert country name to ISO 2-letter country code."""
    country_codes = {
        "Poland": "PL",
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

def normalize_phone(phone: str, country_code: str) -> str:
    """Normalize phone number format based on country."""
    if not phone:
        return "+48500600700" if country_code == "PL" else "+441403740350"
    
    # Basic normalization - remove non-digit characters
    digits = ''.join(c for c in phone if c.isdigit())
    
    # Add international prefix if needed
    if not digits.startswith('+'):
        if country_code == "PL" and not digits.startswith('48'):
            digits = f"48{digits}"
        elif country_code == "GB" and not digits.startswith('44'):
            digits = f"44{digits}"
        return f"+{digits}"
    return phone

def get_shipping_details(shipping: Dict, country_code: str) -> Tuple[str, str, str]:
    """Determine shipping details based on address and country."""
    street = shipping.get("Line1", "Unknown Street")
    postcode = shipping.get("Postcode", "00-001") if country_code == "PL" else shipping.get("Postcode", "00000")
    city = shipping.get("City", "Unknown City")
    return street, postcode, city

def get_carrier_and_currency(country_code: str, order_data: Dict) -> Tuple[str, str]:
    """Determine carrier and currency based on country."""
    carrier = "Kurier InPost - ShipX" if country_code == "PL" else "FedEx"
    currency = order_data.get("SaleOrderCurrency") or order_data.get("Currency") or ("PLN" if country_code == "PL" else "EUR")
    return carrier, currency

# === API Clients ===
class Cin7Client:
    def __init__(self):
        self.base_url = "https://inventory.dearsystems.com/ExternalApi/v2"
        self.headers = {
            "Content-Type": "application/json",
            "api-auth-accountid": Config.CORE_ACCOUNT_ID,
            "api-auth-applicationkey": Config.CORE_APP_KEY
        }
    
    def test_api_connection(self) -> bool:
        """Test if we can connect to the Cin7 API."""
        url = f"{self.base_url}/saleList"
        params = {
            "Page": 1,
            "Limit": 1,
            "UpdatedSince": (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"API connection test failed: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"API response: {e.response.text}")
            return False
    
    def get_orders(self, start_date: datetime, end_date: datetime, status: str = None) -> List[Dict]:
        """Fetch orders from Cin7 within a date range with pagination support."""
        all_orders = []
        page = 1
        
        logger.debug(f"Fetching orders from {start_date} to {end_date} with status '{status}'")
        
        while True:
            url = f"{self.base_url}/saleList"
            params = {
                "Page": page,
                "Limit": Config.MAX_BATCH_SIZE,
                "UpdatedSince": start_date.strftime("%Y-%m-%dT%H:%M:%S"),
                "UpdatedTo": end_date.strftime("%Y-%m-%dT%H:%M:%S")
            }
            
            if status and status != "ALL":
                params["Status"] = status
            
            logger.debug(f"Requesting page {page} with params: {params}")
            
            try:
                response = requests.get(url, headers=self.headers, params=params)
                logger.debug(f"API response status: {response.status_code}")
                
                response.raise_for_status()
                data = response.json()
                
                orders = data.get("SaleList", [])
                logger.debug(f"Received {len(orders)} orders in page {page}")
                
                if not orders:
                    break  # No more orders
                
                all_orders.extend(orders)
                
                # Check if we've got all available orders
                if len(orders) < Config.MAX_BATCH_SIZE:
                    break
                    
                page += 1
                
            except Exception as e:
                logger.error(f"Failed to fetch orders from Cin7 (page {page}): {str(e)}")
                if hasattr(e, 'response') and e.response is not None:
                    logger.error(f"API response content: {e.response.text}")
                break
        
        logger.info(f"Total orders fetched: {len(all_orders)}")
        if all_orders:
            logger.info(f"Sample order numbers: {[o['SaleOrderNumber'] for o in all_orders[:3]]}")
        return all_orders
    
    def get_order_details(self, sale_id: str) -> Optional[Dict]:
        """Get detailed information about a specific order."""
        url = f"{self.base_url}/sale?ID={sale_id}&CombineAdditionalCharges=true"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch order details for {sale_id}: {str(e)}")
            return None
    
    def update_tracking(self, sale_id: str, tracking_number: str, tracking_url: str = None) -> bool:
        """Update tracking information in Cin7."""
        if not tracking_url:
            tracking_url = Config.TRACKING_URL_TEMPLATE.format(tracking_number)
        
        url = f"{self.base_url}/sale/{sale_id}/fulfilment/ship"
        payload = {
            "trackingNumber": tracking_number,
            "trackingURL": tracking_url
        }
        
        try:
            response = requests.put(url, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error updating tracking for order {sale_id}: {str(e)}")
            return False
    
    def authorize_pick(self, task_id: str, lines: List[Dict]) -> bool:
        """Authorize picking for an order."""
        url = f"{self.base_url}/sale/fulfilment/pick"
        payload = {
            "TaskID": task_id,
            "Status": "AUTHORISED",
            "Lines": lines
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error authorizing pick for task {task_id}: {str(e)}")
            return False
    
    def authorize_pack(self, task_id: str, lines: List[Dict]) -> bool:
        """Authorize packing for an order."""
        url = f"{self.base_url}/sale/fulfilment/pack"
        payload = {
            "TaskID": task_id,
            "Status": "AUTHORISED",
            "Lines": lines
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error authorizing pack for task {task_id}: {str(e)}")
            return False
    
    def authorize_ship(self, task_id: str, tracking_number: str, tracking_url: str, 
                      shipping_address: Dict, lines: List[Dict]) -> bool:
        """Authorize shipping for an order."""
        url = f"{self.base_url}/sale/fulfilment/ship"
        payload = {
            "TaskID": task_id,
            "Status": "AUTHORISED",
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
                "ShipToOther": shipping_address.get("ShipToOther", "")
            },
            "ShippingNotes": shipping_address.get("ShippingNotes", ""),
            "Lines": [{
                "ShipmentDate": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "Carrier": shipping_address.get("Carrier", "InPost"),
                "Box": Config.DEFAULT_BOX,
                "TrackingNumber": tracking_number,
                "TrackingURL": tracking_url,
                "IsShipped": True
            }]
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error authorizing ship for task {task_id}: {str(e)}")
            return False

class InPostClient:
    def __init__(self):
        self.base_url = "https://api-inpost.linker.shop/public-api/v1"
        self.api_key = Config.INPOST_API_KEY
        self.headers = {"Content-Type": "application/json"}
    
    def create_order(self, order_data: Dict) -> Union[Dict, bool]:
        """Create an order in InPost and return the response."""
        url = f"{self.base_url}/orders?apikey={self.api_key}"
        try:
            response = requests.post(url, headers=self.headers, json=order_data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to create order {order_data.get('clientOrderNumber', '')} in InPost: {str(e)}")
            return False
    
    def get_tracking_info(self, order_id: str) -> Optional[Dict]:
        """Get tracking information for an existing order."""
        url = f"{self.base_url}/orders/{order_id}?apikey={self.api_key}"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get tracking info for order {order_id}: {str(e)}")
            return None
    
    def get_todays_orders(self) -> Optional[Dict]:
        """Get today's orders from InPost."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        url = f"{self.base_url}/orders?createdAt={today}&apikey={self.api_key}"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get today's orders from InPost: {str(e)}")
            return None

# === Order Processing ===
class OrderProcessor:
    def __init__(self):
        self.cin7 = Cin7Client()
        self.inpost = InPostClient()
        self.processed_orders = set()
        self.synced_orders = {}  # Track orders that have been synced but need fulfillment updates
        self.load_processed_orders()
    
    def load_processed_orders(self):
        """Load previously processed orders from files."""
        try:
            with open('processed_orders.json', 'r') as f:
                self.processed_orders = set(json.load(f))
        except (FileNotFoundError, json.JSONDecodeError):
            self.processed_orders = set()
        
        try:
            with open('synced_orders.json', 'r') as f:
                self.synced_orders = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.synced_orders = {}
    
    def save_processed_orders(self):
        """Save processed orders to files."""
        with open('processed_orders.json', 'w') as f:
            json.dump(list(self.processed_orders), f)
        
        with open('synced_orders.json', 'w') as f:
            json.dump(self.synced_orders, f)
    
    def process_new_orders(self):
        """Check for and process new orders."""
        # Calculate date range - look back 1 hour to catch any missed orders
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(hours=1)
        
        logger.info(f"Checking for new orders between {start_date} and {end_date}")
        
        # Get orders from Cin7
        orders = self.cin7.get_orders(start_date, end_date, Config.ORDER_STATUS_FILTER)
        
        if not orders:
            logger.info("No new orders found")
            return
        
        logger.info(f"Found {len(orders)} new orders to process")
        
        success_count = 0
        for order in orders:
            order_id = order["ID"]
            order_number = order["SaleOrderNumber"]
            
            # Skip if already processed
            if order_id in self.processed_orders:
                logger.debug(f"Skipping already processed order {order_number}")
                continue
            
            # Process the order
            if self.process_order(order_id, order_number):
                success_count += 1
                self.processed_orders.add(order_id)
        
        # Check for tracking updates on previously synced orders
        self.check_tracking_and_fulfillment()
        
        # Save processed orders
        self.save_processed_orders()
        logger.info(f"Processed {success_count} new orders successfully")
    
    def process_order(self, sale_id: str, sale_number: str) -> bool:
        """Process a single order from Cin7 to InPost."""
        logger.info(f"Processing order {sale_number}")
        
        # Get order details from Cin7
        order_data = self.cin7.get_order_details(sale_id)
        if not order_data or "Order" not in order_data:
            logger.error(f"Invalid order data for {sale_number}")
            return False
        
        order = order_data["Order"]
        shipping = order_data.get("ShippingAddress", {})
        
        # Extract and validate required fields
        country_name = shipping.get("Country", "Poland")
        country_code = get_country_code(country_name)
        
        # Build order payload for InPost (courier service only)
        inpost_payload = self.build_inpost_courier_payload(order, shipping, country_code)
        
        # Create order in InPost
        response = self.inpost.create_order(inpost_payload)
        if not response:
            return False
        
        # Check if order was created successfully
        if response.get("status", "").lower() != "ok":
            logger.error(f"Failed to create order {sale_number} in InPost: {response.get('message', 'Unknown error')}")
            return False
        
        # Store the Cin7 order details for fulfillment updates
        inpost_order_id = response.get("id")
        if inpost_order_id:
            self.synced_orders[inpost_order_id] = {
                "cin7_order_id": sale_id,
                "cin7_order_number": sale_number,
                "task_id": order_data.get("ID"),  # The TaskID for fulfillment
                "created_at": datetime.now(timezone.utc).isoformat(),
                "tracking_updated": False,
                "pick_authorized": False,
                "pack_authorized": False,
                "ship_authorized": False
            }
            logger.info(f"Successfully created InPost order {inpost_order_id} for Cin7 order {sale_number}")
            return True
        
        return False
    
    def check_tracking_and_fulfillment(self):
        """Check for tracking numbers and complete fulfillment in Cin7."""
        if not self.synced_orders:
            return
        
        logger.info(f"Checking tracking and fulfillment for {len(self.synced_orders)} synced orders")
        
        updated_count = 0
        for inpost_order_id, order_info in list(self.synced_orders.items()):
            if all([order_info.get("tracking_updated", False),
                   order_info.get("pick_authorized", False),
                   order_info.get("pack_authorized", False),
                   order_info.get("ship_authorized", False)]):
                continue  # Skip already completed orders
            
            # Get tracking info from InPost
            tracking_info = self.inpost.get_tracking_info(inpost_order_id)
            if not tracking_info:
                continue
            
            tracking_number = tracking_info.get("trackingNumber")
            tracking_url = tracking_info.get("trackingURL")
            
            if not tracking_number:
                continue  # Skip if no tracking number yet
            
            # Get order details from Cin7 for fulfillment
            order_data = self.cin7.get_order_details(order_info["cin7_order_id"])
            if not order_data or "Order" not in order_data:
                continue
            
            # Update tracking if not already done
            if not order_info.get("tracking_updated", False):
                if self.cin7.update_tracking(
                    order_info["cin7_order_id"],
                    tracking_number,
                    tracking_url
                ):
                    order_info["tracking_updated"] = True
                    order_info["tracking_number"] = tracking_number
                    order_info["tracking_url"] = tracking_url
                    updated_count += 1
                    logger.info(f"Updated tracking for order {order_info['cin7_order_number']}: {tracking_number}")
                else:
                    logger.error(f"Failed to update tracking for order {order_info['cin7_order_number']}")
                    continue
            
            # Prepare fulfillment lines
            lines = []
            for line in order_data["Order"]["Lines"]:
                if line.get("SKU") and line.get("ProductID") != "00000000-0000-0000-0000-000000000000":
                    lines.append({
                        "ProductID": line["ProductID"],
                        "SKU": line["SKU"],
                        "Name": line["Name"],
                        "Location": Config.DEFAULT_LOCATION,
                        "Quantity": line["Quantity"]
                    })
            
            # Authorize pick if not already done
            if not order_info.get("pick_authorized", False) and lines:
                if self.cin7.authorize_pick(order_info["task_id"], lines):
                    order_info["pick_authorized"] = True
                    logger.info(f"Authorized pick for order {order_info['cin7_order_number']}")
                else:
                    logger.error(f"Failed to authorize pick for order {order_info['cin7_order_number']}")
                    continue
            
            # Prepare pack lines with box information
            pack_lines = []
            for line in lines:
                pack_line = line.copy()
                pack_line["Box"] = Config.DEFAULT_BOX
                pack_lines.append(pack_line)
            
            # Authorize pack if not already done
            if not order_info.get("pack_authorized", False) and pack_lines:
                if self.cin7.authorize_pack(order_info["task_id"], pack_lines):
                    order_info["pack_authorized"] = True
                    logger.info(f"Authorized pack for order {order_info['cin7_order_number']}")
                else:
                    logger.error(f"Failed to authorize pack for order {order_info['cin7_order_number']}")
                    continue
            
            # Authorize ship if not already done
            if not order_info.get("ship_authorized", False) and tracking_number:
                shipping_address = order_data.get("ShippingAddress", {})
                if self.cin7.authorize_ship(
                    order_info["task_id"],
                    tracking_number,
                    tracking_url,
                    shipping_address,
                    pack_lines
                ):
                    order_info["ship_authorized"] = True
                    logger.info(f"Authorized ship for order {order_info['cin7_order_number']}")
                else:
                    logger.error(f"Failed to authorize ship for order {order_info['cin7_order_number']}")
                    continue
            
            # If we got here, all steps were successful
            updated_count += 1
        
        if updated_count:
            logger.info(f"Updated tracking and fulfillment for {updated_count} orders")
            self.save_processed_orders()
    
    def build_inpost_courier_payload(self, order_data: Dict, shipping: Dict, country_code: str) -> Dict:
        """Build the payload for InPost Courier API (no delivery point)."""
        # Extract items and calculate total weight
        items = []
        total_weight = 0.0
        
        for line in order_data["Lines"]:
            sku = line.get("SKU", line.get("Sku", ""))
            if sku == "" or line.get("ProductID") == "00000000-0000-0000-0000-000000000000":
                continue  # skip placeholder shipping lines

            item_weight = float(line.get("ProductWeight", Config.DEFAULT_ITEM_WEIGHT_KG * 1000)) / 1000  # convert g to kg
            total_weight += item_weight * float(line["Quantity"])

            items.append({
                "sku": sku,
                "externalId": line["ProductID"],
                "ordered": line["Quantity"],
                "quantity": line["Quantity"],
                "description": line["Name"],
                "weight": item_weight,
                "vat_code": 23,
                "price_gross": float(line["Price"]),
                "price_net": float(line["Total"])
            })

        # Ensure minimum weight
        total_weight = max(total_weight, Config.DEFAULT_WEIGHT_KG)
        
        # Get shipping details (no delivery point for courier)
        street, postcode, city = get_shipping_details(shipping, country_code)
        carrier, currency = get_carrier_and_currency(country_code, order_data)
        
        # Calculate totals
        price_gross = sum(item['price_gross'] for item in items)
        
        # Build payload for courier service
        payload = {
            "clientOrderNumber": order_data["SaleOrderNumber"],
            "externalId": order_data["SaleOrderNumber"],
            "paymentMethod": currency,
            "currencySymbol": currency,
            "orderDate": order_data.get("SaleOrderDate", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")),
            "carrier": carrier,
            "deliveryRecipient": order_data.get("Customer", "Unknown Customer"),
            "deliveryPhone": normalize_phone(order_data.get("Phone", ""), country_code),
            "deliveryEmail": order_data.get("Email", "no-email@example.com"),
            "deliveryStreet": street,
            "deliveryPostCode": postcode,
            "deliveryCity": city,
            "deliveryCountry": country_code,
            "depotId": Config.DEPOT_ID,
            "shipmentPrice": 0.00,
            "priceGross": price_gross,
            "weight": total_weight,
            "items": items,
            "comments": f"Automated sync from Cin7 order {order_data['SaleOrderNumber']}",
            "service": "courier"  # Explicitly specify courier service
        }
        
        return payload

# === Main Execution ===
def main():
    processor = OrderProcessor()
    
    # First test the API connection
    if not processor.cin7.test_api_connection():
        logger.error("Failed to connect to Cin7 API. Check credentials and network connection.")
        return
    
    # Initial sync - look back further to catch any missed orders
    logger.info("Starting initial sync...")
    initial_end = datetime.now(timezone.utc)
    initial_start = initial_end - timedelta(hours=Config.INITIAL_LOOKBACK_HOURS)
    
    logger.info(f"Looking for orders between {initial_start} and {initial_end}")
    
    initial_orders = processor.cin7.get_orders(initial_start, initial_end, Config.ORDER_STATUS_FILTER)
    logger.info(f"Found {len(initial_orders)} orders in initial sync period")
    
    # Log the order numbers if we found any
    if initial_orders:
        logger.info(f"Order numbers found: {[o['SaleOrderNumber'] for o in initial_orders[:5]]}")
    
    success_count = 0
    for order in initial_orders:
        order_id = order["ID"]
        order_number = order["SaleOrderNumber"]
        
        if order_id not in processor.processed_orders:
            if processor.process_order(order_id, order_number):
                success_count += 1
                processor.processed_orders.add(order_id)
    
    processor.save_processed_orders()
    logger.info(f"Initial sync complete. Processed {success_count} orders.")
    
    # Check for any pending tracking updates
    processor.check_tracking_and_fulfillment()
    
    # Continuous polling
    logger.info("Starting continuous polling for new orders...")
    while True:
        try:
            processor.process_new_orders()
        except Exception as e:
            logger.error(f"Error during order processing: {str(e)}")
        
        time.sleep(Config.POLL_INTERVAL)

if __name__ == "__main__":
    main()