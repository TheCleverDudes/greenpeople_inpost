<?php
    include('function.php');
    echo '<pre>';
    $page = '10';
   $get_all_products_page_wise = get_all_products_page_wise($page);
   
   $x=1;
   foreach($get_all_products_page_wise['Products'] as $get_all_products_page_wiseeeeess){
      
        $product_id = $get_all_products_page_wiseeeeess['ID'];
        $product_SKU = $get_all_products_page_wiseeeeess['SKU'];
        if($product_SKU == '870366' or $product_SKU == 'AK03'){
            
        }else{
       $get_product_images=get_product_images($product_id);
        
        $imagess=[];
        foreach($get_product_images as $get_product_imagesssss){
           
            $imagess[]= $get_product_imagesssss['DownloadUrl'];
        }
        
       $Name= $get_all_products_page_wiseeeeess['Name'];
       $SKU = $get_all_products_page_wiseeeeess['SKU'];
       $Barcode = $get_all_products_page_wiseeeeess['Barcode'];
       $Category = $get_all_products_page_wiseeeeess['Category'];
       $Weight = $get_all_products_page_wiseeeeess['Weight'];
       $WeightUnits = $get_all_products_page_wiseeeeess['WeightUnits'];
       $Length = $get_all_products_page_wiseeeeess['Length'];
       $Width = $get_all_products_page_wiseeeeess['Width'];
       $Height = $get_all_products_page_wiseeeeess['Height'];
       $DimensionsUnits = $get_all_products_page_wiseeeeess['DimensionsUnits'];
       $unit = 'szt';
       
       
        $payload_array=array(
                        "name" => $Name,
                        "sku" => $SKU,
                        "barcode" => $Barcode,
                        "category" => $Category,
                        "unit" => $unit,
                        "weight" => $Weight,
                        "weightUnit" => $WeightUnits,
                        "length" => $Length,
                        "width" => $Width,
                        "depth" => $Height,
                        "storageUnits" => [],
                        "images" => $imagess,
                        "dimensionsUnit" => $DimensionsUnits
            );
             $json_encode=json_encode($payload_array,1);
             
             $create_products_inside_InPost=create_products_inside_InPost($json_encode);
        }
       
        $x++;
   }
 
