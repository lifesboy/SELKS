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
            $flags = explode('<', explode('flags=', $line)[1])[0];
            $mtu = explode('mtu ', $line)[1];
            $stats[$current_interface]['mtu'] = trim($mtu);
            $stats[$current_interface]['flags'] = trim($flags);
            $stats[$current_interface]['input errors'] = 0;
            $stats[$current_interface]['output errors'] = 0;
            $stats[$current_interface]['collisions'] = 0;
//            flags: 8010
//            promiscuous listeners: 0
//            send queue length: 0
//            send queue max length: 50
//            send queue drops: 0
//            type: PPP
//            physical: unknown physical 0
//            address length: 0
//            header length: 0
//            link state: 0
//            vhid: 0
//            datalen: 152
//            mtu: 1500
//            metric: 0
//            line rate: 0 bit/s
//            packets received: 0
//            input errors: 0
//            packets transmitted: 0
//            output errors: 0
//            collisions: 0
//            bytes received: 0
//            bytes transmitted: 0
//            multicasts received: 0
//            multicasts transmitted: 0
//            input queue drops: 0
//            packets for unknown protocol: 0
//            HW offload capabilities: 0x0
//            uptime at attach or stat reset: 19
        }
        elseif (strpos($line, 'TX errors') > 0) {
            $output_errors = explode(' ', explode('TX errors ', $line)[1])[0];
            $collisions = explode('collisions ', $line)[1];
            $stats[$current_interface]['collisions'] = trim($collisions);
            $stats[$current_interface]['output errors'] = trim($output_errors);
        }
        elseif (strpos($line, 'RX errors') > 0) {
            $input_errors = explode(' ', explode('RX errors ', $line)[1])[0];
            $stats[$current_interface]['input errors'] = trim($input_errors);
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