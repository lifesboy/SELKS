<?php

// Find all possible media options for the interface
$mediaopts_list = array();
$optlist_intf = ['em2'];//get_parent_interface($pconfig['if']);
if (count($optlist_intf) > 0) {
//    exec("/sbin/ifconfig -m {$optlist_intf[0]} | grep \"media \"", $mediaopts);
//    foreach ($mediaopts as $mediaopt){
//        preg_match("/media (.*)/", $mediaopt, $matches);
//        if (preg_match("/(.*) mediaopt (.*)/", $matches[1], $matches1)){
//            // there is media + mediaopt like "media 1000baseT mediaopt full-duplex"
//            array_push($mediaopts_list, $matches1[1] . " " . $matches1[2]);
//        } else {
//            // there is only media like "media 1000baseT"
//            array_push($mediaopts_list, $matches[1]);
//        }
//    }
    $mediaopts_list = [
        'autoselect',
        '1000baseT',
        '1000baseT full-duplex',
        '100baseTX full-duplex',
        '100baseTX',
        '10baseT/UTP full-duplex',
        '10baseT/UTP'
    ];
}

var_dump($mediaopts_list);

?>