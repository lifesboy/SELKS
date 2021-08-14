
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
    exec("grep MemAvailable /proc/meminfo | awk '{print $2}'" . " 2>&1", $physmem);
    exec("grep MemTotal /proc/meminfo | awk '{print $2}'" . " 2>&1", $realmem);

    /* convert from kilobytes to megabytes */
    return array((intval($physmem) / 1024),(intval($realmem) / 1024));
}

$res = get_memory();
var_dump($res);