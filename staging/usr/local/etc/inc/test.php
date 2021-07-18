<?php

function mask2cidr($mask)
{
  $long = ip2long($mask);
  $base = ip2long('255.255.255.255');
  return 32-log(($long ^ $base)+1,2);
}

function legacy_interfaces_details($intf = null)
{
    $result = array();
    if (!empty($intf)) {
        $tmp_intf = escapeshellarg($intf);
    } else {
        $tmp_intf = '';
    }

    $cmd = '/sbin/ifconfig -a ' . $tmp_intf;
    exec($cmd . ' 2>&1', $ifconfig_data, $ret);
    if ($ret) {
        /* only error if no explicit interface was choosen */
        if (empty($intf)) {
            log_error('The command `' . $cmd . '\' failed to execute ' . implode(' ', $ifconfig_data));
        }
        return $result;
    }

    $current_interface = null;
    foreach ($ifconfig_data as $line) {
        $line_parts = explode(' ', trim($line));
        echo $line;
        var_dump($line_parts);
        if (strpos(trim($line), 'flags=') !== false && $line[0] != "\t") {
            $current_interface = explode(':', $line)[0];
            $result[$current_interface] = array();
            //$result[$current_interface]["capabilities"] = array();
            $result[$current_interface]["capabilities"] = ['RXCSUM' , 'TXCSUM' , 'VLAN_MTU'];
//            $result[$current_interface]["options"] = array();
            $result[$current_interface]["options"] = ['VLAN_MTU'];
            $result[$current_interface]["macaddr"] = "00:00:00:00:00:00";
            $result[$current_interface]["ipv4"] = array();
            $result[$current_interface]["ipv6"] = array();
            if (preg_match("/ mtu ([0-9]*).*$/", $line, $matches)) {
                $result[$current_interface]["mtu"] = $matches[1];
            }
            if (preg_match("/<[A-Z,]+>/", $line, $matches)) {
                $flags = explode(',', substr($matches[0], 1, strlen($matches[0]) - 2));
                if (array_search('UP', $flags) >= 0) {
                    $result[$current_interface]['status'] = 'active';
                }
            }
        } elseif (empty($current_interface)) {
            // skip parsing, no interface found (yet)
            continue;
//        } elseif (strpos(trim($line), 'capabilities=') !== false) {
//            // parse capabilities
//            // $capabilities = substr($line, strpos($line, '<') + 1, -1);
//            $capabilities = 'RXCSUM,TXCSUM,VLAN_MTU';
//            foreach (explode(',', $capabilities) as $capability) {
//                $result[$current_interface]["capabilities"][] = strtolower(trim($capability));
//            }
//        } elseif (strpos(trim($line), 'options=') !== false) {
//            // parse options
//            // $options = substr($line, strpos($line, '<') + 1, -1);
//            $options = 'VLAN_MTU';
//            foreach (explode(',', $options) as $option) {
//                $result[$current_interface]["options"][] = strtolower(trim($option));
//            }
        } elseif (strpos($line, "ether ") !== false) {
            // mac address
            $result[$current_interface]["macaddr"] = $line_parts[1];
        } elseif (strpos($line, "inet ") !== false) {
            // IPv4 information
            unset($mask);
            unset($vhid);
            for ($i = 0; $i < count($line_parts) - 1; ++$i) {
                if ($line_parts[$i] == 'netmask') {
                    // $mask = substr_count(base_convert(hexdec($line_parts[$i + 1]), 10, 2), '1');
                    $mask = mask2cidr($line_parts[$i + 1]);
                } elseif ($line_parts[$i] == 'vhid') {
                    $vhid = $line_parts[$i + 1];
                }
            }
            if (isset($mask)) {
                $tmp = array("ipaddr" => $line_parts[1], "subnetbits" => $mask);
                if ($line_parts[2] == '-->') {
                    $tmp['endpoint'] = $line_parts[3];
                }
                if (isset($vhid)) {
                    $tmp['vhid'] = $vhid;
                }
                $result[$current_interface]["ipv4"][] = $tmp;
            }
            echo '=======mask=======';
            var_dump($mask);
            var_dump($vhid);
        } elseif (strpos($line, "inet6 ") !== false) {
            // IPv6 information
            $addr = strtok($line_parts[1], '%');
            $tmp = array('ipaddr' => $addr, 'link-local' => strpos($addr, 'fe80:') === 0, 'tunnel' => false);
            for ($i = 0; $i < count($line_parts) - 1; ++$i) {
                if ($line_parts[$i] == 'prefixlen') {
                    $tmp['subnetbits'] = intval($line_parts[$i + 1]);
                } elseif ($line_parts[$i] == 'vhid') {
                    $tmp['vhid'] = $line_parts[$i + 1];
                }
                if ($line_parts[$i] == '-->') {
                    $tmp['tunnel'] = true;
                    $tmp['endpoint'] = $line_parts[$i + 1];
                }
            }
            if (isset($tmp['subnetbits'])) {
                $result[$current_interface]["ipv6"][] = $tmp;
                // sort link local to bottom, leave rest of sorting as-is (primary address on top)
                usort($result[$current_interface]["ipv6"], function ($a, $b) {
                    return $a['link-local'] - $b['link-local'];
                });
            }
            echo '=======inet6=======';
            var_dump($result[$current_interface]["ipv6"]);

//        } elseif (strpos($line, "\ttunnel ") !== false) {
//            // extract tunnel proto, source and destination
//            $result[$current_interface]["tunnel"] = array();
//            $result[$current_interface]["tunnel"]["proto"] = $line_parts[1];
//            $result[$current_interface]["tunnel"]["src_addr"] = $line_parts[2];
//            $result[$current_interface]["tunnel"]["dest_addr"] = $line_parts[4];
//        } elseif (preg_match("/media: (.*)/", $line, $matches)) {
//            // media, when link is between parenthesis grep only the link part
//            $result[$current_interface]['media'] = $matches[1];
//            if (preg_match("/media: .*? \((.*?)\)/", $line, $matches)) {
//                $result[$current_interface]['media'] = $matches[1];
//            }
//            $result[$current_interface]['media_raw'] = substr(trim($line), 7);
//        } elseif (preg_match("/status: (.*)$/", $line, $matches)) {
//            $result[$current_interface]['status'] = $matches[1];
//        } elseif (preg_match("/channel (\S*)/", $line, $matches)) {
//            $result[$current_interface]['channel'] = $matches[1];
//        } elseif (preg_match("/ssid (\".*?\"|\S*)/", $line, $matches)) {
//            $result[$current_interface]['ssid'] = $matches[1];
//        } elseif (preg_match("/laggproto (.*)$/", $line, $matches)) {
//            $result[$current_interface]['laggproto'] = $matches[1];
//        } elseif (preg_match("/laggport: (.*)$/", $line, $matches)) {
//            if (empty($result[$current_interface]['laggport'])) {
//                $result[$current_interface]['laggport'] = array();
//            }
//            $result[$current_interface]['laggport'][] = explode(' ', trim($matches[1]))[0];
//        } elseif (strpos($line, "\tgroups: ") !== false) {
//            array_shift($line_parts);
//            $result[$current_interface]['groups'] = $line_parts;
//        } elseif (strpos($line, "\tcarp: ") !== false) {
//            if (empty($result[$current_interface]["carp"])) {
//                $result[$current_interface]["carp"] = array();
//            }
//            $result[$current_interface]["carp"][] = array(
//                "status" => $line_parts[1],
//                "vhid" => $line_parts[3],
//                "advbase" => $line_parts[5],
//                "advskew" => $line_parts[7]
//            );
//        } elseif (strpos($line, "\tvxlan") !== false) {
//            if (empty($result[$current_interface]["vxlan"])) {
//                $result[$current_interface]["vxlan"] = array();
//            }
//            $result[$current_interface]["vxlan"]["vni"] = $line_parts[2];
//            $result[$current_interface]["vxlan"]["local"] = $line_parts[4];
//            if ($line_parts[5] == "group") {
//                $result[$current_interface]["vxlan"]["group"] = $line_parts[6];
//            } else {
//                $result[$current_interface]["vxlan"]["remote"] = $line_parts[6];
//            }
//        }
    }

    echo '===========RESULT========';
    var_dump($result);

    return $result;
}
legacy_interfaces_details();
$ip = "255.255.255.0";
echo mask2cidr($ip);

?>