<?php
  
  //get all products from the cin7core with the limit of 20 
   function get_all_products_page_wise($page){
                   $curl = curl_init();
            
                    curl_setopt_array($curl, array(
                      CURLOPT_URL => "https://inventory.dearsystems.com/ExternalApi/v2/product?Page=$page&Limit=20",
                      CURLOPT_RETURNTRANSFER => true,
                      CURLOPT_ENCODING => '',
                      CURLOPT_MAXREDIRS => 10,
                      CURLOPT_TIMEOUT => 0,
                      CURLOPT_FOLLOWLOCATION => true,
                      CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
                      CURLOPT_CUSTOMREQUEST => 'GET',
                      CURLOPT_HTTPHEADER => array(
                        'Content-Type: application/json',
                        'api-auth-accountid: 3384f900-b8b1-41bc-8324-1e6000e897ec',
                        'api-auth-applicationkey: c1bf7dbf-5365-9d50-95a1-960ee4455445',
                        'Cookie: DEARAffinity=1c8086f6bee5867d714c634b297a636f; DEARAffinityCORS=1c8086f6bee5867d714c634b297a636f'
                      ),
                    ));
                    
                    $response = curl_exec($curl);
                    
                    curl_close($curl);
                   return json_decode($response,1);
           }
           
    // create products inside the InPost
    function create_products_inside_InPost($json_encode){
                $curl = curl_init();
                
                curl_setopt_array($curl, array(
                  CURLOPT_URL => 'https://api-inpost.linker.shop/public-api/v1/products?apikey=da3f39f46c9f473d29cc8ec40a0ae787',
                  CURLOPT_RETURNTRANSFER => true,
                  CURLOPT_ENCODING => '',
                  CURLOPT_MAXREDIRS => 10,
                  CURLOPT_TIMEOUT => 0,
                  CURLOPT_FOLLOWLOCATION => true,
                  CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
                  CURLOPT_CUSTOMREQUEST => 'POST',
                  CURLOPT_POSTFIELDS => $json_encode,
                  CURLOPT_HTTPHEADER => array(
                    'Content-Type: application/json'
                  ),
                ));
                
                $response = curl_exec($curl);
                
                curl_close($curl);
                return (json_decode($response,1));
    }
    
    //get  product images
    function get_product_images($product_id){
                $curl = curl_init();
        
                    curl_setopt_array($curl, array(
                      CURLOPT_URL => "https://inventory.dearsystems.com/ExternalApi/v2/product/attachments?ProductID=$product_id",
                      CURLOPT_RETURNTRANSFER => true,
                      CURLOPT_ENCODING => '',
                      CURLOPT_MAXREDIRS => 10,
                      CURLOPT_TIMEOUT => 0,
                      CURLOPT_FOLLOWLOCATION => true,
                      CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
                      CURLOPT_CUSTOMREQUEST => 'GET',
                      CURLOPT_HTTPHEADER => array(
                        'Content-Type: application/json',
                        'api-auth-accountid: 3384f900-b8b1-41bc-8324-1e6000e897ec',
                        'api-auth-applicationkey: c1bf7dbf-5365-9d50-95a1-960ee4455445',
                        'Cookie: DEARAffinity=1c8086f6bee5867d714c634b297a636f; DEARAffinityCORS=1c8086f6bee5867d714c634b297a636f'
                      ),
                    ));
                    
                    $response = curl_exec($curl);
                    
                    curl_close($curl);
                    return json_decode($response,1);
    }



    //get sale order from Green People IE
    
     function get_sale_order($SaleID){
             $curl = curl_init();
                 
                 curl_setopt_array($curl, array(
                  CURLOPT_URL => "https://inventory.dearsystems.com/ExternalApi/v2/sale?ID=$SaleID&CombineAdditionalCharges=true",
                  CURLOPT_RETURNTRANSFER => true,
                  CURLOPT_ENCODING => '',
                  CURLOPT_MAXREDIRS => 10,
                  CURLOPT_TIMEOUT => 0,
                  CURLOPT_FOLLOWLOCATION => true,
                  CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
                  CURLOPT_CUSTOMREQUEST => 'GET',
                  CURLOPT_SSL_VERIFYPEER => false, // Add this line to bypass SSL check for local testing
                  CURLOPT_HTTPHEADER => array(
                    'Content-Type: application/json',
                    'api-auth-accountid: 3384f900-b8b1-41bc-8324-1e6000e897ec',
                    'api-auth-applicationkey: c1bf7dbf-5365-9d50-95a1-960ee4455445',
                    'Cookie: DEARAffinity=1c8086f6bee5867d714c634b297a636f; DEARAffinityCORS=1c8086f6bee5867d714c634b297a636f'
                  ),
                ));
            
            $response = curl_exec($curl);
            $http_code = curl_getinfo($curl, CURLINFO_HTTP_CODE);

            // --- DEBUG: Log everything from the API call ---
            file_put_contents('sale_order_http_code.log', $http_code);
            file_put_contents('sale_order_raw_response.log', $response);

            // Add cURL error handling
            if (curl_errno($curl)) {
                $error_msg = curl_error($curl);
                file_put_contents('sale_order_curl_error.log', $error_msg);
            }
            
            curl_close($curl);
            return json_decode($response,1);
     }
     
     //create order inside the InPost
      //  function create_sale_order_inpost($encode_payload){
      //      $curl = curl_init();
      //           curl_setopt_array($curl, array(
      //             CURLOPT_URL => 'https://api-inpost.linker.shop/public-api/v1/orders?apikey=da3f39f46c9f473d29cc8ec40a0ae787',
      //             CURLOPT_RETURNTRANSFER => true,
      //             CURLOPT_ENCODING => '',
      //             CURLOPT_MAXREDIRS => 10,
      //             CURLOPT_TIMEOUT => 0,
      //             CURLOPT_FOLLOWLOCATION => true,
      //             CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
      //             CURLOPT_CUSTOMREQUEST => 'POST',
      //             CURLOPT_POSTFIELDS =>$encode_payload,
      //             CURLOPT_HTTPHEADER => array(
      //               'Content-Type: application/json'
      //             ),
      //           ));
                
      //           $response = curl_exec($curl);
                
      //           curl_close($curl);
      //           return json_decode($response,1);

      //  }

      function create_sale_order_inpost($payload_array) {
          $encodedPayload = json_encode($payload_array, JSON_PRETTY_PRINT); // Makes logs readable
      
          $curl = curl_init();
      
          curl_setopt_array($curl, array(
              CURLOPT_URL => 'https://api-inpost.linker.shop/public-api/v1/orders?apikey=da3f39f46c9f473d29cc8ec40a0ae787',
              CURLOPT_RETURNTRANSFER => true,
              CURLOPT_ENCODING => '',
              CURLOPT_MAXREDIRS => 10,
              CURLOPT_TIMEOUT => 30,
              CURLOPT_FOLLOWLOCATION => true,
              CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
              CURLOPT_CUSTOMREQUEST => 'POST',
              CURLOPT_POSTFIELDS => $encodedPayload,
              CURLOPT_SSL_VERIFYPEER => false, // consider turning this ON in production
              CURLOPT_HTTPHEADER => array(
                  'Content-Type: application/json',
                  'Content-Length: ' . strlen($encodedPayload)
              ),
          ));
      
          $response = curl_exec($curl);
          $httpCode = curl_getinfo($curl, CURLINFO_HTTP_CODE);
      
          // Log any cURL-level error
          if (curl_errno($curl)) {
              echo "❌ cURL Error: " . curl_error($curl) . "\n";
          }
      
          // Log response if the HTTP code indicates a problem
          if ($httpCode < 200 || $httpCode >= 300) {
              echo "\n❌ InPost API Error (HTTP $httpCode)\n";
              echo "➡️ Payload Sent:\n$encodedPayload\n";
              echo "⬅️ Response:\n$response\n";
          } else {
              echo "\n✅ InPost API Success (HTTP $httpCode)\n";
              echo "🆔 Order created with response:\n$response\n";
          }
      
          curl_close($curl);
          return json_decode($response, true);
      }
     
         
        //all products from the InPost 
        function get_all_products_from_InPost(){
            $curl = curl_init();

            curl_setopt_array($curl, array(
              CURLOPT_URL => 'https://api-inpost.linker.shop/public-api/v1/products?apikey=da3f39f46c9f473d29cc8ec40a0ae787&page=2',
              CURLOPT_RETURNTRANSFER => true,
              CURLOPT_ENCODING => '',
              CURLOPT_MAXREDIRS => 10,
              CURLOPT_TIMEOUT => 0,
              CURLOPT_FOLLOWLOCATION => true,
              CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
              CURLOPT_CUSTOMREQUEST => 'GET',
              CURLOPT_HTTPHEADER => array(
                'Content-Type: application/json'
              ),
            ));
            
            $response = curl_exec($curl);
            
            curl_close($curl);
            return json_decode($response,1);
        }
        
        //get PO from the core using the id
        function get_PO_using_id($PO_id){
            $curl = curl_init();

            curl_setopt_array($curl, array(
              CURLOPT_URL => "https://inventory.dearsystems.com/ExternalApi/v2/advanced-purchase?ID=$PO_id&CombineAdditionalCharges=true",
              CURLOPT_RETURNTRANSFER => true,
              CURLOPT_ENCODING => '',
              CURLOPT_MAXREDIRS => 10,
              CURLOPT_TIMEOUT => 0,
              CURLOPT_FOLLOWLOCATION => true,
              CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
              CURLOPT_CUSTOMREQUEST => 'GET',
              CURLOPT_SSL_VERIFYPEER => false, // Add this line to bypass SSL check for local testing
              CURLOPT_HTTPHEADER => array(
                'Content-Type: application/json',
                'api-auth-accountid: 3384f900-b8b1-41bc-8324-1e6000e897ec',
                'api-auth-applicationkey: c1bf7dbf-5365-9d50-95a1-960ee4455445',
                'Cookie: DEARAffinity=1c8086f6bee5867d714c634b297a636f; DEARAffinityCORS=1c8086f6bee5867d714c634b297a636f'
              ),
            ));
            
            $response = curl_exec($curl);

            // Add cURL error handling
            if (curl_errno($curl)) {
                $error_msg = curl_error($curl);
                file_put_contents('curl_error.log', $error_msg);
            }

            file_put_contents('cin7_response.json', $response);
            
            curl_close($curl);
            return json_decode($response,1);
        }
        
        //get supplier details
        function get_suppllier_data($supplier_id){
            $curl = curl_init();

            curl_setopt_array($curl, array(
              CURLOPT_URL => "https://inventory.dearsystems.com/ExternalApi/v2/supplier?ID=$supplier_id",
              CURLOPT_RETURNTRANSFER => true,
              CURLOPT_ENCODING => '',
              CURLOPT_MAXREDIRS => 10,
              CURLOPT_TIMEOUT => 0,
              CURLOPT_FOLLOWLOCATION => true,
              CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
              CURLOPT_CUSTOMREQUEST => 'GET',
              CURLOPT_HTTPHEADER => array(
                'Content-Type: application/json',
                'api-auth-accountid: 3384f900-b8b1-41bc-8324-1e6000e897ec',
                'api-auth-applicationkey: c1bf7dbf-5365-9d50-95a1-960ee4455445',
                'Cookie: DEARAffinity=1c8086f6bee5867d714c634b297a636f; DEARAffinityCORS=1c8086f6bee5867d714c634b297a636f'
              ),
            ));
            
            $response = curl_exec($curl);
            
            curl_close($curl);
            return json_decode($response,1);
            }
        
      
        //create PO inside the InPost
        function create_PO_inside_InPost($encode_payload){
            $curl = curl_init();
            curl_setopt_array($curl, array(
              CURLOPT_URL => 'https://api-inpost.linker.shop/public-api/v1/supplierorders?apikey=da3f39f46c9f473d29cc8ec40a0ae787',
              CURLOPT_RETURNTRANSFER => true,
              CURLOPT_ENCODING => '',
              CURLOPT_MAXREDIRS => 10,
              CURLOPT_TIMEOUT => 0,
              CURLOPT_FOLLOWLOCATION => true,
              CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
              CURLOPT_CUSTOMREQUEST => 'POST',
              CURLOPT_SSL_VERIFYPEER => false, // Add this line to bypass SSL check for local testing
              CURLOPT_POSTFIELDS => $encode_payload,
              CURLOPT_HTTPHEADER => array(
                'Content-Type: application/json'
              ),
            ));
            
            $response = curl_exec($curl);

            // Add cURL error handling
            if (curl_errno($curl)) {
                $error_msg = curl_error($curl);
                // Log error to a specific file for this function
                file_put_contents('inpost_curl_error.log', $error_msg);
            }
            
            curl_close($curl);
            return json_decode($response,1);
        }

        function check_inpost_po_exists($clientOrderNumber) {
            $curl = curl_init();
            $url = "https://api-inpost.linker.shop/public-api/v1/supplierorders?apikey=da3f39f46c9f473d29cc8ec40a0ae787&clientOrderNumber=$clientOrderNumber";
        
            curl_setopt_array($curl, array(
                CURLOPT_URL => $url,
                CURLOPT_RETURNTRANSFER => true,
                CURLOPT_HTTPHEADER => ['Content-Type: application/json'],
            ));
        
            $response = curl_exec($curl);
            curl_close($curl);
        
            $decoded = json_decode($response, true);
            return !empty($decoded['items']);
        }

        function check_inpost_so_exists($clientOrderNumber) {
            $url = "https://api-inpost.linker.shop/public-api/v1/orders?apikey=da3f39f46c9f473d29cc8ec40a0ae787&clientOrderNumber=$clientOrderNumber";
        
            $curl = curl_init();
            curl_setopt_array($curl, array(
                CURLOPT_URL => $url,
                CURLOPT_RETURNTRANSFER => true,
                CURLOPT_HTTPHEADER => array('Content-Type: application/json'),
            ));
        
            $response = curl_exec($curl);
            curl_close($curl);
        
            $data = json_decode($response, true);
            return isset($data['items']) && count($data['items']) > 0;
        }
      
      
        
        //get the PO from INPOST which delivery status is closed(Y)
        function PO_from_InPOST_delivery_status_closed($current_date){
            $curl = curl_init();

            curl_setopt_array($curl, array(
              CURLOPT_URL => "https://api-inpost.linker.shop/public-api/v1/supplierorders?apikey=da3f39f46c9f473d29cc8ec40a0ae787&filters[order_date]=$current_date&filters[order_status]=Y",
              CURLOPT_RETURNTRANSFER => true,
              CURLOPT_ENCODING => '',
              CURLOPT_MAXREDIRS => 10,
              CURLOPT_TIMEOUT => 0,
              CURLOPT_FOLLOWLOCATION => true,
              CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
              CURLOPT_CUSTOMREQUEST => 'GET',
            ));
            
            $response = curl_exec($curl);
            
            curl_close($curl);
            return json_decode($response,1);

        }
        
        //search PO number in core
        function serach_PO_in_core($PO_number){
            $curl = curl_init();

            curl_setopt_array($curl, array(
              CURLOPT_URL => "https://inventory.dearsystems.com/ExternalApi/v2/purchaseList?Search=$PO_number",
              CURLOPT_RETURNTRANSFER => true,
              CURLOPT_ENCODING => '',
              CURLOPT_MAXREDIRS => 10,
              CURLOPT_TIMEOUT => 0,
              CURLOPT_FOLLOWLOCATION => true,
              CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
              CURLOPT_CUSTOMREQUEST => 'GET',
              CURLOPT_HTTPHEADER => array(
                'Content-Type: application/json',
                'api-auth-accountid: 3384f900-b8b1-41bc-8324-1e6000e897ec',
                'api-auth-applicationkey: c1bf7dbf-5365-9d50-95a1-960ee4455445',
                'Cookie: DEARAffinity=1c8086f6bee5867d714c634b297a636f; DEARAffinityCORS=1c8086f6bee5867d714c634b297a636f'
              ),
            ));
            
            $response = curl_exec($curl);
            
            curl_close($curl);
            return json_decode($response,1);

        }
        
        //update PO in core as stock received
        function PO_stock_received($PO_id_from_core,$payload){
            $curl = curl_init();

            curl_setopt_array($curl, array(
              CURLOPT_URL => "https://inventory.dearsystems.com/ExternalApi/v2/advanced-purchase/stock?PurchaseID=$PO_id_from_core",
              CURLOPT_RETURNTRANSFER => true,
              CURLOPT_ENCODING => '',
              CURLOPT_MAXREDIRS => 10,
              CURLOPT_TIMEOUT => 0,
              CURLOPT_FOLLOWLOCATION => true,
              CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
              CURLOPT_CUSTOMREQUEST => 'POST',
              CURLOPT_POSTFIELDS =>'{
                "TaskID": "'.$PO_id_from_core.'",
                "Status": "AUTHORISED",
                "Lines": '.$payload.'
            }',
              CURLOPT_HTTPHEADER => array(
                'Content-Type: application/json',
                'api-auth-accountid: 3384f900-b8b1-41bc-8324-1e6000e897ec',
                'api-auth-applicationkey: c1bf7dbf-5365-9d50-95a1-960ee4455445',
                'Cookie: DEARAffinity=1c8086f6bee5867d714c634b297a636f; DEARAffinityCORS=1c8086f6bee5867d714c634b297a636f'
              ),
            ));
            
            $response = curl_exec($curl);
            
            curl_close($curl);
            return json_decode($response,1);
        }
        
        //fetch country code using country name
        $countryNameToCode = array(
                                    "Afghanistan" => "AF",
                                    "Albania" => "AL",
                                    "Algeria" => "DZ",
                                    "Andorra" => "AD",
                                    "Angola" => "AO",
                                    "Antigua and Barbuda" => "AG",
                                    "Argentina" => "AR",
                                    "Armenia" => "AM",
                                    "Australia" => "AU",
                                    "Austria" => "AT",
                                    "Azerbaijan" => "AZ",
                                    "Bahamas" => "BS",
                                    "Bahrain" => "BH",
                                    "Bangladesh" => "BD",
                                    "Barbados" => "BB",
                                    "Belarus" => "BY",
                                    "Belgium" => "BE",
                                    "Belize" => "BZ",
                                    "Benin" => "BJ",
                                    "Bhutan" => "BT",
                                    "Bolivia" => "BO",
                                    "Bosnia and Herzegovina" => "BA",
                                    "Botswana" => "BW",
                                    "Brazil" => "BR",
                                    "Brunei" => "BN",
                                    "Bulgaria" => "BG",
                                    "Burkina Faso" => "BF",
                                    "Burundi" => "BI",
                                    "Cabo Verde" => "CV",
                                    "Cambodia" => "KH",
                                    "Cameroon" => "CM",
                                    "Canada" => "CA",
                                    "Central African Republic" => "CF",
                                    "Chad" => "TD",
                                    "Chile" => "CL",
                                    "China" => "CN",
                                    "Colombia" => "CO",
                                    "Comoros" => "KM",
                                    "Congo, Democratic Republic of the" => "CD",
                                    "Congo, Republic of the" => "CG",
                                    "Costa Rica" => "CR",
                                    "Croatia" => "HR",
                                    "Cuba" => "CU",
                                    "Cyprus" => "CY",
                                    "Czech Republic" => "CZ",
                                    "Denmark" => "DK",
                                    "Djibouti" => "DJ",
                                    "Dominica" => "DM",
                                    "Dominican Republic" => "DO",
                                    "Ecuador" => "EC",
                                    "Egypt" => "EG",
                                    "El Salvador" => "SV",
                                    "Equatorial Guinea" => "GQ",
                                    "Eritrea" => "ER",
                                    "Estonia" => "EE",
                                    "Eswatini" => "SZ",
                                    "Ethiopia" => "ET",
                                    "Fiji" => "FJ",
                                    "Finland" => "FI",
                                    "France" => "FR",
                                    "Gabon" => "GA",
                                    "Gambia" => "GM",
                                    "Georgia" => "GE",
                                    "Germany" => "DE",
                                    "Ghana" => "GH",
                                    "Greece" => "GR",
                                    "Grenada" => "GD",
                                    "Guatemala" => "GT",
                                    "Guinea" => "GN",
                                    "Guinea-Bissau" => "GW",
                                    "Guyana" => "GY",
                                    "Haiti" => "HT",
                                    "Honduras" => "HN",
                                    "Hungary" => "HU",
                                    "Iceland" => "IS",
                                    "India" => "IN",
                                    "Indonesia" => "ID",
                                    "Iran" => "IR",
                                    "Iraq" => "IQ",
                                    "Ireland" => "IE",
                                    "Israel" => "IL",
                                    "Italy" => "IT",
                                    "Jamaica" => "JM",
                                    "Japan" => "JP",
                                    "Jordan" => "JO",
                                    "Kazakhstan" => "KZ",
                                    "Kenya" => "KE",
                                    "Kiribati" => "KI",
                                    "Korea, North" => "KP",
                                    "Korea, South" => "KR",
                                    "Kuwait" => "KW",
                                    "Kyrgyzstan" => "KG",
                                    "Laos" => "LA",
                                    "Latvia" => "LV",
                                    "Lebanon" => "LB",
                                    "Lesotho" => "LS",
                                    "Liberia" => "LR",
                                    "Libya" => "LY",
                                    "Liechtenstein" => "LI",
                                    "Lithuania" => "LT",
                                    "Luxembourg" => "LU",
                                    "Madagascar" => "MG",
                                    "Malawi" => "MW",
                                    "Malaysia" => "MY",
                                    "Maldives" => "MV",
                                    "Mali" => "ML",
                                    "Malta" => "MT",
                                    "Marshall Islands" => "MH",
                                    "Mauritania" => "MR",
                                    "Mauritius" => "MU",
                                    "Mexico" => "MX",
                                    "Micronesia" => "FM",
                                    "Moldova" => "MD",
                                    "Monaco" => "MC",
                                    "Mongolia" => "MN",
                                    "Montenegro" => "ME",
                                    "Morocco" => "MA",
                                    "Mozambique" => "MZ",
                                    "Myanmar" => "MM",
                                    "Namibia" => "NA",
                                    "Nauru" => "NR",
                                    "Nepal" => "NP",
                                    "Netherlands" => "NL",
                                    "New Zealand" => "NZ",
                                    "Nicaragua" => "NI",
                                    "Niger" => "NE",
                                    "Nigeria" => "NG",
                                    "North Macedonia" => "MK",
                                    "Norway" => "NO",
                                    "Oman" => "OM",
                                    "Pakistan" => "PK",
                                    "Palau" => "PW",
                                    "Palestine" => "PS",
                                    "Panama" => "PA",
                                    "Papua New Guinea" => "PG",
                                    "Paraguay" => "PY",
                                    "Peru" => "PE",
                                    "Philippines" => "PH",
                                    "Poland" => "PL",
                                    "Portugal" => "PT",
                                    "Qatar" => "QA",
                                    "Romania" => "RO",
                                    "Russia" => "RU",
                                    "Rwanda" => "RW",
                                    "Saint Kitts and Nevis" => "KN",
                                    "Saint Lucia" => "LC",
                                    "Saint Vincent and the Grenadines" => "VC",
                                    "Samoa" => "WS",
                                    "San Marino" => "SM",
                                    "Sao Tome and Principe" => "ST",
                                    "Saudi Arabia" => "SA",
                                    "Senegal" => "SN",
                                    "Serbia" => "RS",
                                    "Seychelles" => "SC",
                                    "Sierra Leone" => "SL",
                                    "Singapore" => "SG",
                                    "Slovakia" => "SK",
                                    "Slovenia" => "SI",
                                    "Solomon Islands" => "SB",
                                    "Somalia" => "SO",
                                    "South Africa" => "ZA",
                                    "South Sudan" => "SS",
                                    "Spain" => "ES",
                                    "Sri Lanka" => "LK",
                                    "Sudan" => "SD",
                                    "Suriname" => "SR",
                                    "Sweden" => "SE",
                                    "Switzerland" => "CH",
                                    "Syria" => "SY",
                                    "Taiwan" => "TW",
                                    "Tajikistan" => "TJ",
                                    "Tanzania" => "TZ",
                                    "Thailand" => "TH",
                                    "Timor-Leste" => "TL",
                                    "Togo" => "TG",
                                    "Tonga" => "TO",
                                    "Trinidad and Tobago" => "TT",
                                    "Tunisia" => "TN",
                                    "Turkey" => "TR",
                                    "Turkmenistan" => "TM",
                                    "Tuvalu" => "TV",
                                    "Uganda" => "UG",
                                    "Ukraine" => "UA",
                                    "United Arab Emirates" => "AE",
                                    "United Kingdom" => "GB",
                                    "United States" => "US",
                                    "Uruguay" => "UY",
                                    "Uzbekistan" => "UZ",
                                    "Vanuatu" => "VU",
                                    "Vatican City" => "VA",
                                    "Venezuela" => "VE",
                                    "Vietnam" => "VN",
                                    "Yemen" => "YE",
                                    "Zambia" => "ZM",
                                    "Zimbabwe" => "ZW"
                                );
                                
                                function getCountryCode($countryName) {
                                    $countryCodes = [
                                        'united kingdom' => 'GB',
                                        'united states' => 'US',
                                        'poland' => 'PL',
                                        'germany' => 'DE',
                                        'france' => 'FR',
                                        'spain' => 'ES',
                                        'italy' => 'IT',
                                        'netherlands' => 'NL'
                                        // Add more countries as needed
                                    ];

                                    if (empty($countryName)) return null;

                                    $normalizedName = strtolower(trim($countryName));

                                    if (isset($countryCodes[$normalizedName])) {
                                        return $countryCodes[$normalizedName];
                                    }

                                    // Default or fallback code if not found
                                    return null;
                                }
								
								
		//get the ship order from the Inpost
		function Get_Ship_Order_From_inpost($current_date){
			$curl = curl_init();

			curl_setopt_array($curl, array(
			  CURLOPT_URL => "https://api-inpost.linker.shop/public-api/v1/orders?apikey=da3f39f46c9f473d29cc8ec40a0ae787&filters[order_date]=$current_date&filters[order_status]=Y",
			  CURLOPT_RETURNTRANSFER => true,
			  CURLOPT_ENCODING => '',
			  CURLOPT_MAXREDIRS => 10,
			  CURLOPT_TIMEOUT => 0,
			  CURLOPT_FOLLOWLOCATION => true,
			  CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
			  CURLOPT_CUSTOMREQUEST => 'GET',
			));

			$response = curl_exec($curl);

			curl_close($curl);
			 return json_decode($response,1);
		}
								
	//search sale order id by using sale order number							
	 function search_SO_id_using_SO_nu($sale_order_number){
             $curl = curl_init();
        
        curl_setopt_array($curl, array(
          CURLOPT_URL => "https://inventory.dearsystems.com/ExternalApi/v2/saleList?Search=$sale_order_number",
          CURLOPT_RETURNTRANSFER => true,
          CURLOPT_ENCODING => '',
          CURLOPT_MAXREDIRS => 10,
          CURLOPT_TIMEOUT => 0,
          CURLOPT_FOLLOWLOCATION => true,
          CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
          CURLOPT_CUSTOMREQUEST => 'GET',
          CURLOPT_HTTPHEADER => array(
            'Content-Type: application/json',
            'api-auth-accountid: 3384f900-b8b1-41bc-8324-1e6000e897ec',
            'api-auth-applicationkey: c1bf7dbf-5365-9d50-95a1-960ee4455445',
            'Cookie: DEARAffinity=1c8086f6bee5867d714c634b297a636f; DEARAffinityCORS=1c8086f6bee5867d714c634b297a636f'
          ),
        ));
        
        $response = curl_exec($curl);
        
        curl_close($curl);
        return json_decode($response,1);
        
         }
		 
		  //get data using sale order id
     function get_data_using_sale_order_id($sale_order_id){
         $curl = curl_init();
            
            curl_setopt_array($curl, array(
              CURLOPT_URL => "https://inventory.dearsystems.com/ExternalApi/v2/sale?ID=$sale_order_id&CombineAdditionalCharges=true",
              CURLOPT_RETURNTRANSFER => true,
              CURLOPT_ENCODING => '',
              CURLOPT_MAXREDIRS => 10,
              CURLOPT_TIMEOUT => 0,
              CURLOPT_FOLLOWLOCATION => true,
              CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
              CURLOPT_CUSTOMREQUEST => 'GET',
              CURLOPT_HTTPHEADER => array(
                'Content-Type: application/json',
                'api-auth-accountid: 3384f900-b8b1-41bc-8324-1e6000e897ec',
               'api-auth-applicationkey: c1bf7dbf-5365-9d50-95a1-960ee4455445',
                'Cookie: DEARAffinity=1c8086f6bee5867d714c634b297a636f; DEARAffinityCORS=1c8086f6bee5867d714c634b297a636f'
              ),
            ));
            
            $response = curl_exec($curl);
            
            curl_close($curl);
            return json_decode($response,1);

     }
	 
	 //SO pick authorized
	 function SO_pick_authorized($pick_payload){
            $curl = curl_init();

                curl_setopt_array($curl, array(
                  CURLOPT_URL => 'https://inventory.dearsystems.com/ExternalApi/v2/sale/fulfilment/pick',
                  CURLOPT_RETURNTRANSFER => true,
                  CURLOPT_ENCODING => '',
                  CURLOPT_MAXREDIRS => 10,
                  CURLOPT_TIMEOUT => 0,
                  CURLOPT_FOLLOWLOCATION => true,
                  CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
                  CURLOPT_CUSTOMREQUEST => 'POST',
                  CURLOPT_POSTFIELDS => $pick_payload,
                  CURLOPT_HTTPHEADER => array(
                    'Content-Type: application/json',
                   'api-auth-accountid: 3384f900-b8b1-41bc-8324-1e6000e897ec',
                   'api-auth-applicationkey: c1bf7dbf-5365-9d50-95a1-960ee4455445',
                    'Cookie: DEARAffinity=1c8086f6bee5867d714c634b297a636f; DEARAffinityCORS=1c8086f6bee5867d714c634b297a636f'
                  ),
                ));
                
                $response = curl_exec($curl);
                
                curl_close($curl);
                return json_decode($response,1);
        }
		
		//SO pack authorized
		 function SO_pack_authorized($pack_payload){
            $curl = curl_init();

            curl_setopt_array($curl, array(
              CURLOPT_URL => 'https://inventory.dearsystems.com/ExternalApi/v2/sale/fulfilment/pack',
              CURLOPT_RETURNTRANSFER => true,
              CURLOPT_ENCODING => '',
              CURLOPT_MAXREDIRS => 10,
              CURLOPT_TIMEOUT => 0,
              CURLOPT_FOLLOWLOCATION => true,
              CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
              CURLOPT_CUSTOMREQUEST => 'POST',
              CURLOPT_POSTFIELDS => $pack_payload,
              CURLOPT_HTTPHEADER => array(
                'Content-Type: application/json',
                'api-auth-accountid: 3384f900-b8b1-41bc-8324-1e6000e897ec',
                'api-auth-applicationkey: c1bf7dbf-5365-9d50-95a1-960ee4455445',
                'Cookie: DEARAffinity=1c8086f6bee5867d714c634b297a636f; DEARAffinityCORS=1c8086f6bee5867d714c634b297a636f'
              ),
            ));
            
            $response = curl_exec($curl);
            
            curl_close($curl);
            return json_decode($response,1);
        }
		
		//SO ship authorized
		function SO_ship_authorized($shipp_payload){
            $curl = curl_init();

                curl_setopt_array($curl, array(
                  CURLOPT_URL => 'https://inventory.dearsystems.com/ExternalApi/v2/sale/fulfilment/ship',
                  CURLOPT_RETURNTRANSFER => true,
                  CURLOPT_ENCODING => '',
                  CURLOPT_MAXREDIRS => 10,
                  CURLOPT_TIMEOUT => 0,
                  CURLOPT_FOLLOWLOCATION => true,
                  CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
                  CURLOPT_CUSTOMREQUEST => 'POST',
                  CURLOPT_POSTFIELDS => $shipp_payload,
                  CURLOPT_HTTPHEADER => array(
                    'Content-Type: application/json',
                    'api-auth-accountid: 3384f900-b8b1-41bc-8324-1e6000e897ec',
                    'api-auth-applicationkey: c1bf7dbf-5365-9d50-95a1-960ee4455445',
                    'Cookie: DEARAffinity=1c8086f6bee5867d714c634b297a636f; DEARAffinityCORS=1c8086f6bee5867d714c634b297a636f'
                  ),
                ));
                
                $response = curl_exec($curl);
                
                curl_close($curl);
                return json_decode($response,1);

        }
		
		//get the  product details from the core
		function Get_Product_details_using_P_ID($product_id){
			$curl = curl_init();

			curl_setopt_array($curl, array(
			  CURLOPT_URL => "https://inventory.dearsystems.com/ExternalApi/v2/product?ID=$product_id",
			  CURLOPT_RETURNTRANSFER => true,
			  CURLOPT_ENCODING => '',
			  CURLOPT_MAXREDIRS => 10,
			  CURLOPT_TIMEOUT => 0,
			  CURLOPT_FOLLOWLOCATION => true,
			  CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
			  CURLOPT_CUSTOMREQUEST => 'GET',
			  CURLOPT_HTTPHEADER => array(
				'Content-Type: application/json',
				'api-auth-accountid: 3384f900-b8b1-41bc-8324-1e6000e897ec',
				'api-auth-applicationkey: c1bf7dbf-5365-9d50-95a1-960ee4455445',
				'Cookie: DEARAffinity=1c8086f6bee5867d714c634b297a636f; DEARAffinityCORS=1c8086f6bee5867d714c634b297a636f'
			  ),
			));

			$response = curl_exec($curl);

			curl_close($curl);
			return json_decode($response,1);
		}

    //update tracking in core
    function update_tracking_in_core($sale_order_id, $tracking_number, $tracking_url){
      $curl = curl_init();

      curl_setopt_array($curl, array(
        CURLOPT_URL => "https://inventory.dearsystems.com/ExternalApi/v2/sale/$sale_order_id/fulfilment/ship",
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_ENCODING => '',
        CURLOPT_MAXREDIRS => 10,
        CURLOPT_TIMEOUT => 0,
        CURLOPT_FOLLOWLOCATION => true,
        CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
        CURLOPT_CUSTOMREQUEST => 'PUT',
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

      curl_close($curl);
      return json_decode($response,1);
    }