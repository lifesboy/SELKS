
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
//
//$res = get_memory();
//var_dump($res);


function system_default_route($gateway, $family, $interface, $far = false)
{
    $realif = ""; // get_real_interface($interface, $family == 'inet' ? 'all' : 'inet6');

    switch ($family) {
        case 'inet':
            break;
        case 'inet6':
            if (is_linklocal($gateway)) {
                $gateway .= "%{$realif}";
            }
            break;
        default:
            log_error("ROUTING: unknown address family '{$family}'");
            return;
    }

    $tmpcmd = "/sbin/route -n get -{$family} default 2>/dev/null | /usr/bin/awk '/gateway:/ {print $2}'";
    $current = trim(exec($tmpcmd), " \n");
    if ($current == $gateway) {
        log_error("ROUTING: keeping current default gateway '{$gateway}'");
        return;
    }

    if ($family == 'inet') {
        foreach (glob('/tmp/*_defaultgw') as $to_delete) {
            log_error("ROUTING: removing {$to_delete}");
            @unlink($to_delete);
        }

        log_error("ROUTING: creating /tmp/{$realif}_defaultgw using '{$gateway}'");
        @file_put_contents("/tmp/{$realif}_defaultgw", $gateway);

        if (!$far) {
            $realif = null;
        }
    } else {
        foreach (glob('/tmp/*_defaultgwv6') as $to_delete) {
            log_error("ROUTING: removing {$to_delete}");
            @unlink($to_delete);
        }

        log_error("ROUTING: creating /tmp/{$realif}_defaultgwv6 using '{$gateway}'");
        @file_put_contents("/tmp/{$realif}_defaultgwv6", $gateway);

        /* IPv6 does not support far gateway notion */
        $realif = null;
    }

    mwexecf('/sbin/route delete -%s default', array($family), true);
    if (!empty($realif)) {
        mwexecf('/sbin/route delete -%s %s -interface %s', array($family, $gateway, $realif), true);
        mwexecf('/sbin/route add -%s %s -interface %s', array($family, $gateway, $realif));
    }
    mwexecf('/sbin/route add -%s default %s', array($family, $gateway));
}

function system_routing_configure($verbose = false, $interface = '')
{
    if ($verbose) {
        echo 'Setting up routes...';
        flush();
    }

    if (!empty($interface)) {
        log_error("ROUTING: entering configure using '${interface}'");
    } else {
        log_error("ROUTING: entering configure using defaults");
    }

    $gateways = new \OPNsense\Routing\Gateways(legacy_interfaces_details());

    foreach (['inet', 'inet6'] as $ipproto) {
        /* determine default gateway without considering monitor status */
        $gateway = $gateways->getDefaultGW(array(), $ipproto);
        $logproto = $ipproto == 'inet' ? 'IPv4' : 'IPv6';
        if ($gateway != null) {
            log_error("ROUTING: {$logproto} default gateway set to {$gateway['interface']}");
            if ((empty($interface) || $interface == $gateway['interface']) && !empty($gateway['gateway'])) {
                log_error("ROUTING: setting {$logproto} default route to {$gateway['gateway']}");
                system_default_route($gateway['gateway'], $ipproto, $gateway['interface'], isset($gateway['fargw']));
            } else {
                log_error("ROUTING: skipping {$logproto} default route");
            }
        }
    }

    system_staticroutes_configure($interface);

    set_sysctl(array(
        'net.inet.ip.forwarding' => '1',
        'net.inet6.ip6.forwarding' => '1',
    ));

    if ($verbose) {
        echo "done.\n";
    }
}

function mwexec($command, $mute = false)
{
    $oarr = array();
    $retval = 0;

    $garbage = exec("{$command} 2>&1", $oarr, $retval);
    unset($garbage);

    if ($retval != 0 && $mute == false) {
        $output = implode(' ', $oarr);
        log_error(sprintf("The command '%s' returned exit code '%d', the output was '%s'", $command, $retval, $output));
        unset($output);
    }

    unset($oarr);

    return $retval;
}

function exec_safe($format, $args = array())
{
    if (!is_array($args)) {
        /* just in case there's only one argument */
        $args = array($args);
    }

    foreach ($args as $id => $arg) {
        $args[$id] = escapeshellarg($arg);
    }

    return vsprintf($format, $args);
}

function mwexecf($format, $args = array(), $mute = false)
{
    return mwexec(exec_safe($format, $args), $mute);
}



//$res = system_routing_configure(true);
//var_dump($res);

$res = mwexecf('%s', '/usr/sbin/service ray restart && ray status', true);
var_dump($res);