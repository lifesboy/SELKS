<?php

function legacy_interface_listget($flag = '')
{
    $cmd_wlan = 'sysctl -n net.wlan.devices';
    $cmd = '/sbin/ifconfig -a | grep "flags"';
    $ifs_wlan = null;
    $ifs = null;

//    exec($cmd_wlan . ' 2>&1', $out_wlan, $ret_wlan);
//    if (!$ret_wlan && !empty($out_wlan[0])) {
//        $ifs_wlan = explode(' ', $out_wlan[0]);
//    }

    if ($flag === 'up') {
        $cmd .= ' | grep "UP"';
    } elseif ($flag === 'down') {
        $cmd .= ' | grep "DOWN"';
    }

    exec($cmd . ' 2>&1', $out, $ret);
    if ($ret) {
        log_error('The command `' . $cmd . '\' failed to execute');
        return ($ifs);
    }

    var_dump($out);
    if (isset($out) && count($out) > 0) {
        $ifs = array_map(function ($line) {
            return explode(':', $line)[0];
        }, $out);
    }

    if ($ifs_wlan != null) {
        $ifs = array_merge($ifs, $ifs_wlan);
    }

    return ($ifs);
}

$list = legacy_interface_listget();
var_dump($list);