<?php

/**
 * PHP function to create a new Order in InPost Fulfillment.
 *
 * This function sends a POST request to the InPost 'Order: Create' endpoint.
 * It constructs a sample payload based on the InPost API documentation (Page 20-22).
 *
 * IMPORTANT:
 * - Replace 'YOUR_API_KEY' with your actual InPost API key.
 * - Replace all placeholder values with your dynamic order data.
 * - This function requires a valid JSON payload for the order details.
 * - Ensure your server allows outgoing cURL requests.
 *
 * @param array $orderPayload The array containing the order details.
 * @return array The decoded JSON response from the InPost API.
 */
function createInpostOrder($orderPayload) {
    // InPost Production API Base URL (as per documentation Page 2)
    // For testing, you might want to switch to the test environment:
    // 'https://api-inpost-test.linker.shop/public-api/v1/orders?apikey=YOUR_API_KEY'
    $apiUrl = 'https://api-inpost.linker.shop/public-api/v1/orders';

    // Replace 'YOUR_API_KEY' with your actual API key
    // It's recommended to store API keys securely, not directly in code.
    $apiKey = 'da3f39f46c9f473d29cc8ec40a0ae787'; // <<< IMPORTANT: REPLACE WITH YOUR ACTUAL API KEY

    // Construct the full URL with the API key
    $fullUrl = $apiUrl . '?apikey=' . $apiKey;

    // Encode the payload array into a JSON string
    $encodedPayload = json_encode($orderPayload);

    // Initialize cURL session
    $curl = curl_init();

    // Set cURL options
    curl_setopt_array($curl, array(
        CURLOPT_URL => 'https://api-inpost.linker.shop/public-api/v1/orders?apikey=da3f39f46c9f473d29cc8ec40a0ae787',
        CURLOPT_RETURNTRANSFER => true, // Return the response as a string
        CURLOPT_ENCODING => '',        // Handle all encodings
        CURLOPT_MAXREDIRS => 10,       // Follow up to 10 HTTP redirects
        CURLOPT_TIMEOUT => 30,         // Timeout after 30 seconds
        CURLOPT_FOLLOWLOCATION => true,// Follow Location headers
        CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1, // Use HTTP/1.1
        CURLOPT_CUSTOMREQUEST => 'POST', // Set request method to POST
        CURLOPT_POSTFIELDS => $encodedPayload, // Set the JSON payload
        CURLOPT_SSL_VERIFYPEER => false,
        CURLOPT_HTTPHEADER => array(
            'Content-Type: application/json', // Set Content-Type header
            'Content-Length: ' . strlen($encodedPayload) // Set Content-Length header
        ),
    ));

    // Execute the cURL request and get the response
    $response = curl_exec($curl);

    // Check for cURL errors
    if (curl_errno($curl)) {
        echo 'cURL Error: ' . curl_error($curl);
        return ['error' => curl_error($curl)];
    }

    // Get HTTP status code
    $httpCode = curl_getinfo($curl, CURLINFO_HTTP_CODE);

    // Close cURL session
    curl_close($curl);

    // Decode the JSON response and return
    $decodedResponse = json_decode($response, true);

    // Add HTTP code to response for debugging
    $decodedResponse['http_code'] = $httpCode;

    return $decodedResponse;
}

// --- Example Usage ---

// Define a sample payload for a new order
// This is based on the "Request BODY" example on Page 22-23 of your document.
// You MUST replace these with your actual order data.
$sampleOrderPayload = [
    "clientOrderNumber" => "SO-TEST", // Required: Your order number
    "externalId" => "SO-TEST",       // Required: Your order ID
    "paymentMethod" => "EUR",                         // Required: Payment method (e.g., "PRZELEW" for bank transfer)
    "orderDate" => date("Y-m-d H:i:s"),                   // Required: Date of order created by receiver
    "carrier" => "INPOST_paczkomat",                      // Required: Your delivery method name
    "deliveryRecipient" => "Test Recipient Name",         // Required: Receiver name & surname
    "deliveryPhone" => "500600700",                       // Required: Receiver phone number
    "deliveryEmail" => "test.recipient@example.com",      // Required: Receiver mail address
    "deliveryStreet" => "Test Street 10",                 // Required: Receiver street & no
    "deliveryPostCode" => "00-001",                       // Required: Receiver post code
    "deliveryCity" => "Warszawa",                         // Required: Receiver city
    "deliveryCountry" => "PL",                            // Required: Country code ISO alpha 2 (e.g., "PL")
    "depotId" => "1234",                                  // Required: Organization Id created by InPost Fulfillment
    "shipmentPrice" => "9.99",                            // Required: Shipment price
    "priceGross" => "29.99",                              // Required: Gross price
    "items" => [                                          // Required: Table with goods to ship in this order
        [
            "sku" => "SKU-TEST",                    // Required: Your SKU for this good
            "externalId" => "SKU-TEST",            // Required: Your ID for this SKU
            "ordered" => 1,                               // Required: Quantity to ship
            "quantity" => 1,                              // Required: Quantity to ship (Note: document shows "1.000" as string, but float/int is fine)
            "description" => "CLEVER TEST",       // Required: Product's Name
            "weight" => 0.126,                            // Required: Weight (e.g., in kg)
            "vat_code" => "23",                           // Required: Tax code
            "price_gross" => 29.99,                       // Required: Gross price
            "price_net" => 24.38                          // Required: Net price
        ]
        // Add more items here if needed
    ],
    // Optional fields (from documentation):
    // "additionalOrderNumber" => "ADD_ORDER_NUM_XYZ",
    // "executionDate" => date("Y-m-d H:i:s", strtotime("+1 day")),
    // "deliveryCompany" => "TEST Company",
    // "deliveryPointId" => "KKZ01A", // Only if delivering to a specific point (e.g., Paczkomat ID)
    // "deliveryPointName" => "KKZ01A",
    // "codAmount" => "10.00", // Cash On Delivery Amount
    // "comments" => "This is a test order created via API."
];

// Call the function to create the order
$response = createInpostOrder($sampleOrderPayload);

// Output the response for debugging/verification
echo "<pre>";
print_r($response);
echo "</pre>";

?>
