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

//$list = legacy_interface_listget();
//var_dump($list);


function legacy_interface_stats($ifs = null)
{
    if ($ifs != null) {
        // only request data for selected interface
        //$cmd = '/usr/local/sbin/ifinfo ' . escapeshellarg($ifs);
        $cmd = '/usr/sbin/ifconfig -a ' . escapeshellarg($ifs);
    } else {
        // all interfaces
        //$cmd = '/usr/local/sbin/ifinfo';
        $cmd = '/usr/sbin/ifconfig -a';
    }
    $stats = array();

    exec($cmd . ' 2>&1', $out, $ret);
    if ($ret) {
        log_error('The command `' . $cmd . '\' failed to execute');
        return $stats;
    }

    $current_interface = '';
    foreach ($out as $line) {
        if (strpos($line, 'flags=') > 0) {
            $current_interface = explode(':', $line)[0];
            $stats[$current_interface] = array();
            $mtu = explode('mtu ', $line)[1];
            $stats[$current_interface]['mtu'] = trim($mtu);
        }
//        elseif ($current_interface != '') {
//            $stat = explode(':', $line);
//            $stats[$current_interface][trim($stat[0])] = trim($stat[1]);
//        }
    }
    if ($ifs != null) {
        return $stats[$current_interface];
    } else {
        return $stats;
    }
}

$stats = legacy_interface_stats();
var_dump($stats);