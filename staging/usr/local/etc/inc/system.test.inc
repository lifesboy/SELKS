
<?php

/*
 *     get_memory()
 *     returns an array listing the amount of
 *     memory installed in the hardware
 *     [0] net memory available for the OS (FreeBSD) after some is taken by BIOS, video or whatever - e.g. 235 MBytes
 *     [1] real (actual) memory of the system, should be the size of the RAM card/s - e.g. 256 MBytes
 */
function get_memory()
{
//    $physmem = get_single_sysctl("hw.physmem");
//    $realmem = get_single_sysctl("hw.realmem");
    exec("grep MemAvailable /proc/meminfo | awk '{print $2}'" . " 2>&1", $res, $physmem);
    exec("grep MemTotal /proc/meminfo | awk '{print $2}'" . " 2>&1", $res, $realmem);

    /* convert from bytes to megabytes */
    return array(($physmem / 1048576),($realmem / 1048576));
}

$res = get_memory();
var_dump($res);