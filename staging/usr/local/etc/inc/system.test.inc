
<?php

function exec_command($command)
{
    $output = array();
    exec($command . ' 2>&1', $output);
    return(implode("\n", $output));
}

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
    $physmem = exec_command("grep MemAvailable /proc/meminfo | awk '{print $2}'");
    $realmem = exec_command("grep MemTotal /proc/meminfo | awk '{print $2}'");

    echo "MemAvailable:";
    var_dump($physmem);
    echo "MemTotal:";
    var_dump($realmem);

    /* convert from kilobytes to megabytes */
    return array(($physmem / 1024),($realmem / 1024));
}

$res = get_memory();
var_dump($res);