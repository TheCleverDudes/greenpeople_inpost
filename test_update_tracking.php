<?php
include('function.php');

$sale_order_id = '287289f5-31fa-4b5c-8c27-884bc61c22c2';
$tracking_number = 'TESTTRACK123456';
$tracking_url = 'https://tracking.example.com/TESTTRACK123456';

// Call the function, but copy the code here for debugging
$curl = curl_init();

curl_setopt_array($curl, array(
    CURLOPT_URL => "https://inventory.dearsystems.com/ExternalApi/v2/sale/$sale_order_id/fulfilment/ship",
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_ENCODING => '',
    CURLOPT_MAXREDIRS => 10,
    CURLOPT_TIMEOUT => 0,
    CURLOPT_FOLLOWLOCATION => true,
    CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
    CURLOPT_CUSTOMREQUEST => 'POST',
    CURLOPT_POSTFIELDS => json_encode(array(
        'trackingNumber' => $tracking_number,
        'trackingURL' => $tracking_url
    )),
    CURLOPT_HTTPHEADER => array(
        'Content-Type: application/json',
        'api-auth-accountid: 3384f900-b8b1-41bc-8324-1e6000e897ec',
        'api-auth-applicationkey: c1bf7dbf-5365-9d50-95a1-960ee4455445',
        'Cookie: DEARAffinity=1c8086f6bee5867d714c634b297a636f; DEARAffinityCORS=1c8086f6bee5867d714c634b297a636f'
    ),
));

$response = curl_exec($curl);

if (curl_errno($curl)) {
    echo "CURL ERROR: " . curl_error($curl) . "\n";
}

$http_code = curl_getinfo($curl, CURLINFO_HTTP_CODE);

curl_close($curl);

echo "HTTP Code: $http_code\n";
echo "Raw Response:\n$response\n";
echo "Decoded Response:\n";
print_r(json_decode($response,1));