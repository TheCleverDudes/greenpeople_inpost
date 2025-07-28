<?php
include('function.php');
echo '<pre>';

// Read JSON input from webhook
$json = file_get_contents('php://input');

// Require JSON input
if (empty($json)) {
    die("❌ Error: No input received via webhook. Cannot proceed.\n");
}

// Optional: Save JSON for debugging (can be removed or logged differently in production)
file_put_contents('core_sale_order.json', $json);

// Decode JSON
$get_file = json_decode($json, true);
if (!$get_file || !isset($get_file['SaleID'])) {
    die("❌ Error: Invalid JSON or missing 'SaleID'. Cannot proceed.\n");
}

// Fetch sale info
$SaleID = $get_file['SaleID'];
$get_sale_order = get_sale_order($SaleID);

echo "--- Debugging get_sale_order() response ---\n";
print_r($get_sale_order);
echo "\n--- End Debugging ---\n\n";

// Extract fields
$clientOrderNumber     = $get_file['SaleOrderNumber'];
$orderDate             = $get_sale_order['SaleOrderDate'];
$additionalOrderNumber = $get_sale_order['CustomerReference'];
$deliveryRecipient     = $get_sale_order['Customer'];
$deliveryPhone         = $get_sale_order['Phone'];
$deliveryEmail         = $get_sale_order['Email'];
$deliveryStreet        = $get_sale_order['ShippingAddress']['Line1'];
$deliveryPostCode      = $get_sale_order['ShippingAddress']['Postcode'];
$deliveryCity          = $get_sale_order['ShippingAddress']['City'];
$deliveryCountry       = $get_sale_order['ShippingAddress']['Country'];
$deliveryPointId       = $get_sale_order['ShippingAddress']['ID'] ?? null;

// Get country code
$countryCode = getCountryCode($deliveryCountry);

// Determine carrier
$carrier = ($deliveryCountry === 'Poland') ? 'InPost' : 'FedEx';

// Build item list
$item_array = [];
$get_all_products_from_InPost = get_all_products_from_InPost();

foreach ($get_sale_order['Order']['Lines'] as $items) {
    $sku         = $items['SKU'];
    $quantity    = $items['Quantity'];
    $description = $items['Name'];
    $priceGross  = (float) $items['Price'];
    $priceNet    = (float) $items['Total'];
    $weight      = isset($items['ProductWeight']) ? (float) $items['ProductWeight'] : 0.1;

    // Match SKU to InPost ID
    $inpost_id = null;
    foreach ($get_all_products_from_InPost['items'] as $product) {
        if ($product['sku'] === $sku) {
            $inpost_id = $product['id'];
            break;
        }
    }

    // Only add valid items
    if ($inpost_id) {
        $item_array[] = [
            'sku'         => $sku,
            'externalId'  => $inpost_id,
            'ordered'     => $quantity,
            'quantity'    => $quantity,
            'description' => $description,
            'weight'      => $weight,
            'vat_code'    => 23,
            'price_gross' => $priceGross,
            'price_net'   => $priceNet
        ];
    } else {
        echo "⚠️ SKU $sku not found in InPost. Skipping item.\n";
    }
}

// Calculate total
$totalGross = array_sum(array_column($item_array, 'price_gross'));

// Final payload
$payload_array = [
    "clientOrderNumber"     => $clientOrderNumber,
    "externalId"            => $clientOrderNumber,
    "additionalOrderNumber" => $additionalOrderNumber,
    "paymentMethod"         => "EUR",
    "currencySymbol"        => "EUR",
    "orderDate"             => $orderDate,
    "carrier"               => $carrier,
    "deliveryRecipient"     => $deliveryRecipient,
    "deliveryPhone"         => $deliveryPhone,
    "deliveryEmail"         => $deliveryEmail,
    "deliveryStreet"        => $deliveryStreet,
    "deliveryPostCode"      => $deliveryPostCode,
    "deliveryCity"          => $deliveryCity,
    "deliveryCountry"       => $countryCode,
    "deliveryPointId"       => $deliveryPointId,
    "depotId"               => "556239",
    "shipmentPrice"         => "0.00",
    "priceGross"            => $totalGross,
    "items"                 => $item_array,
    "comments"              => ""
];

// Prevent duplicate orders
if (!check_inpost_so_exists($clientOrderNumber)) {
    $create_sale_order_inpost = create_sale_order_inpost($payload_array);
    echo "✅ Sales Order created in InPost:\n";
    print_r($create_sale_order_inpost);
} else {
    echo "⚠️ Sales Order $clientOrderNumber already exists in InPost. Skipping.\n";
}
