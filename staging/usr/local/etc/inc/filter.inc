<?php

/*
 * Copyright (C) 2017 Deciso B.V.
 * Copyright (C) 2004-2007 Scott Ullrich <sullrich@gmail.com>
 * Copyright (C) 2005 Bill Marquette <bill.marquette@gmail.com>
 * Copyright (C) 2006 Peter Allgeyer <allgeyer@web.de>
 * Copyright (C) 2008-2010 Ermal Luçi
 * Copyright (C) 2003-2004 Manuel Kasper <mk@neon1.net>
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *
 * 1. Redistributions of source code must retain the above copyright notice,
 *    this list of conditions and the following disclaimer.
 *
 * 2. Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the distribution.
 *
 * THIS SOFTWARE IS PROVIDED ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES,
 * INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY
 * AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
 * AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
 * OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 * SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 * INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
 * CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 * POSSIBILITY OF SUCH DAMAGE.
 */

require_once('filter.lib.inc');

function is_bogonsv6_used()
{
    global $config;

    /*
     * Only use bogonsv6 table if IPv6 Allow is on, and at least
     * one enabled interface also has "blockbogons" enabled.
     */
    $usebogonsv6 = false;

    if (isset($config['system']['ipv6allow']) && isset($config['interfaces'])) {
        foreach ($config['interfaces'] as $ifacedata) {
            if (isset($ifacedata['enable']) && isset($ifacedata['blockbogons'])) {
                $usebogonsv6 = true;
                break;
            }
        }
    }

    return $usebogonsv6;
}

/* sort by interface only, retain the original order of rules that apply to
   the same interface */
function filter_rules_sort()
{
    global $config;

    /* mark each rule with the sequence number (to retain the order while sorting) */
    for ($i = 0; isset($config['filter']['rule'][$i]); $i++) {
        $config['filter']['rule'][$i]['seq'] = $i;
    }
    usort($config['filter']['rule'], function ($a, $b) {
        if (isset($a['floating']) && isset($b['floating'])) {
            return $a['seq'] - $b['seq'];
        } elseif (isset($a['floating'])) {
            return -1;
        } elseif (isset($b['floating'])) {
            return 1;
        } elseif ($a['interface'] == $b['interface']) {
            return $a['seq'] - $b['seq'];
        } elseif ($a['interface'] == $b['interface']) {
            return 0;
        } elseif ($a['interface'] == 'wan') {
            return -1;
        } elseif ($b['interface'] == 'wan') {
            return 1;
        } elseif ($a['interface'] == 'lan') {
            return -1;
        } elseif ($b['interface'] == 'lan') {
            return 1;
        } else {
            return strnatcmp($a['interface'], $b['interface']);
        }
    });
    /* strip the sequence numbers again */
    for ($i = 0; isset($config['filter']['rule'][$i]); $i++) {
        unset($config['filter']['rule'][$i]['seq']);
    }
}

function filter_pflog_start($verbose = false)
{
    if ($verbose) {
        echo 'Starting PFLOG...';
        flush();
    }

    if (isvalidpid('/var/run/filterlog.pid')) {
        killbypid('/var/run/filterlog.pid', 'TERM', true);
    }

    mwexec('/usr/local/sbin/filterlog -i pflog0 -p /var/run/filterlog.pid');

    if ($verbose) {
        echo "done.\n";
    }
}

function filter_configure()
{
    global $config;

    /*
     * NOTE: Check here for bootup status since this should not be triggered during bootup.
     *   The reason is that rc.bootup calls filter_configure_sync directly which does this too.
     */
    if (!file_exists("/var/run/booting")) {
        configd_run('filter reload');
    }
}

function filter_should_trigger_kill_states()
{
    global $config;
    if (empty($config['system']['kill_states'])) {
        $a_gateways = return_gateways_status();
        $ifdetails = legacy_interfaces_details();
        $any_gateway_down = false;
        foreach ((new \OPNsense\Routing\Gateways($ifdetails))->gatewaysIndexedByName(false, true) as $gateway) {
            if (empty($gateway['monitor']) || empty($a_gateways[$gateway['name']])) {
                continue;
            } elseif (!is_ipaddr($gateway['monitor']) || strstr($gateway['monitor'], '127.0.0.')) {
                continue;
            }
            if (stristr($a_gateways[$gateway['name']]['status'], 'down')) {
                $any_gateway_down = true;
                break;
            }
        }
        return $any_gateway_down;
    }
    return false;
}

/**
 * sync interface groups, but leave the ones not managed by us intact.
 */
function ifgroup_setup()
{
    global $config;
    $all_ifgroups = array();
    $all_ifs = array();
    $interface_details = legacy_interfaces_details();
    if (isset($config['ifgroups']['ifgroupentry'])) {
        foreach ($config['ifgroups']['ifgroupentry'] as $group) {
            $all_ifgroups[$group['ifname']] = array();
            foreach (explode(" ", $group['members']) as $member) {
                if (!empty($config['interfaces'][$member])) {
                    $if = $config['interfaces'][$member]['if'];
                    if (!isset($all_ifs[$if])) {
                        $all_ifs[$if] = array();
                    }
                    $all_ifs[$if][] = $group['ifname'];
                    $all_ifgroups[$group['ifname']][] = $if;
                }
            }
        }
    }
    foreach ($interface_details as $intf => $details) {
        $thisifgroups = !empty($details['groups']) ? $details['groups'] : array();
        foreach ($thisifgroups as $ifgroup) {
            if (isset($all_ifgroups[$ifgroup]) && !in_array($intf, $all_ifgroups[$ifgroup])) {
                // detach
                mwexecf('/sbin/ifconfig %s -group %s', array($intf, $ifgroup));
            }
        }
        if (!empty($all_ifs[$intf])) {
            foreach ($all_ifs[$intf] as $ifgroup) {
                if (!in_array($ifgroup, $thisifgroups)) {
                    // attach
                    mwexecf('/sbin/ifconfig %s group %s', array($intf, $ifgroup));
                }
            }
        }
    }
}

/**
 * XXX: replace with check on interfaces section (see pf_interfaces)
 */
function is_interface_group($if)
{
    global $config;

    if (isset($config['ifgroups']['ifgroupentry'])) {
        foreach ($config['ifgroups']['ifgroupentry'] as $groupentry) {
            if ($groupentry['ifname'] === $if) {
                return true;
            }
        }
    }

    return false;
}

function filter_configure_anomaly_rule($run_name, $anomalies)
{
    echo "Configuring anomaly rule for $run_name ...";
    $a_filter = &config_read_array('filter', 'rule');

    $rev = make_config_revision_entry();
    foreach ($anomalies as $i) {
        $a_filter[] = array(
            'type' => 'block',
            'direction' => 'forward',
            'interface' => 'wan',
            'ointerface' => 'lan',
            'ipprotocol' => 'inet',
            'protocol' => 'tcp',
            'source' => array(
                'address' => $i['src_ip'],
            ),
            'destination' => array(
                'address' => $i['dst_ip'],
                'port' => intval($i['dst_port']),
            ),
            'quick' => 0,
            'descr' => $run_name.': AI anomaly auto generated',
            'created' => $rev,
            'updated' => $rev,
        );
    }

    write_config();
}

function filter_configure_sync($verbose = false, $flush_states = false, $load_aliases = true)
{
    global $config;
    $sched_kill_states = array(); // kill states for schedules

    if ($verbose) {
        echo 'Configuring firewall.';
        flush();
    }

    /* Use filter lock to not allow concurrent filter reloads during this run. */
    $filterlck = lock('filter', LOCK_EX);

    ifgroup_setup();
    if ($verbose) {
        echo '.';
        flush();
    }

    // initialize fw plugin object
    $fw = filter_core_get_initialized_plugin_system();
    filter_core_bootstrap($fw);
    $cnfint = iterator_to_array($fw->getInterfaceMapping());
    plugins_firewall($fw);

    if (isset($config['filter']['rule'])) {
        // register user rules
        foreach ($config['filter']['rule'] as $rule) {
            // calculate a hash for this area so we can track this rule, we should replace this
            // with uuid's on the rules like the new style models do eventually.
            $rule_hash = OPNsense\Firewall\Util::calcRuleHash($rule);
            $rule['label'] = $rule_hash;
            $sched = '';
            $descr = '';

            if (!empty($rule['sched'])) {
                $sched = "({$rule['sched']})";
            }
            if (!empty($rule['descr'])) {
                $descr = ": {$rule['descr']}";
            }

            $rule['descr'] = "{$sched}{$descr}";
            if (isset($rule['floating'])) {
                $prio = 200000;
            } elseif (is_interface_group($rule['interface']) || in_array($rule['interface'], array("l2tp", "pptp", "pppoe", "enc0", "openvpn"))) {
                $prio = 300000;
            } else {
                $prio = 400000;
            }
            /* is a time based rule schedule attached? */
            if (!empty($rule['sched']) && !empty($config['schedules'])) {
                foreach ($config['schedules']['schedule'] as $sched) {
                    if ($sched['name'] == $rule['sched']) {
                        if (!filter_get_time_based_rule_status($sched)) {
                            if (!isset($config['system']['schedule_states'])) {
                                $sched_kill_states[] = $rule['label'];
                            }
                            /* disable rule, suffix label to mark end of schedule */
                            $rule['disabled'] = true;
                            $rule['descr'] = "[FIN]" . $rule['descr'];
                        }
                        break;
                    }
                }
            }
            $fw->registerFilterRule($prio, $rule);
        }
    }

    // manual outbound nat rules
    if (
        !empty($config['nat']['outbound']['mode']) &&
          in_array($config['nat']['outbound']['mode'], array("advanced", "hybrid"))
    ) {
        if (!empty($config['nat']['outbound']['rule'])) {
            foreach ($config['nat']['outbound']['rule'] as $rule) {
                $fw->registerSNatRule(100, $rule);
            }
        }
    }

    if (
        empty($config['nat']['outbound']['mode']) ||
          in_array($config['nat']['outbound']['mode'], array("automatic", "hybrid"))
    ) {
        // generate standard outbound rules when mode is automatic ot hybrid
        $intfv4 = array();
        foreach ($fw->getInterfaceMapping() as $intf => $intfcf) {
            if (!empty($intfcf['ifconfig']['ipv4']) && empty($intfcf['gateway'])) {
                $intfv4[] =  $intf;
            }
        }
        // add VPN and local networks
        $intfv4 = array_merge($intfv4, filter_core_get_default_nat_outbound_networks());
        foreach ($fw->getInterfaceMapping() as $intf => $ifcfg) {
            if (substr($ifcfg['if'], 0, 4) != 'ovpn' && !empty($ifcfg['gateway'])) {
                foreach (array(500, null) as $dstport) {
                    $rule = array(
                        "disabled" => true,
                        "interface" => $intf,
                        "dstport" => $dstport,
                        "staticnatport" => !empty($dstport),
                        "destination" => array("any" => true),
                        "ipprotocol" => 'inet',
                        "descr" => "Automatic outbound rule"
                    );
                    foreach ($intfv4 as $network) {
                        $rule['source'] = array("network" => $network);
                        $fw->registerSNatRule(200, $rule);
                    }
                }
            }
        }
    }

    // prevent redirection on ports with "lock out" protection
    foreach (filter_core_get_antilockout() as $lockoutif => $lockoutprts) {
        foreach ($lockoutprts as $port) {
            $rule = array(
                "disabled" => true,
                'interface' => $lockoutif,
                "nordr" => true,
                "protocol" => "tcp",
                'destination' => array('network' => "{$lockoutif}ip", 'port' => $port),
                "descr" => "Anti lockout, prevent redirects for protected ports to this interface ip"
            );
            $fw->registerForwardRule(300, $rule);
        }
    }

    if (!empty($config['nat']['npt'])) {
        // register user npt rules
        foreach ($config['nat']['npt'] as $rule) {
            $fw->registerNptRule(400, $rule);
        }
    }

    if (!empty($config['nat']['onetoone'])) {
        // register user 1:1 mappings
        foreach ($config['nat']['onetoone'] as $rule) {
            $fw->registerDNatRule(500, $rule);
        }
    }
    if (!empty($config['nat']['rule'])) {
        // register user forward rules
        foreach ($config['nat']['rule'] as $rule) {
            $fw->registerForwardRule(600, $rule);
        }
    }

    if (isset($config['system']['gw_switch_default'])) {
        // When gateway switching is enabled, we might consider a different default gateway.
        // although this isn't really the right spot for the feature (it's a monitoring/routing decision),
        // we keep it here for now (historical reasons).
        $down_gateways = return_down_gateways();
        foreach (array("inet", "inet6") as $ipprotocol) {
            if (!empty($down_gateways)) {
                log_error(sprintf("Ignore down %s gateways : %s", $ipprotocol, implode(",", $down_gateways)));
            }
            $default_gw = $fw->getGateways()->getDefaultGW($down_gateways, $ipprotocol);
            if ($default_gw !== null) {
                system_default_route(
                    $default_gw['gateway'],
                    $ipprotocol,
                    $default_gw['if'],
                    isset($default_gw['fargw'])
                );
            }
        }
    }

    $aliases = filter_generate_aliases();
    $aliases .= "\n# Plugins tables\n";
    $aliases .= $fw->tablesToText();

    if ($verbose) {
        echo '.';
        flush();
    }

    $ipsrules = "\n# IPS rules\n";
    $ipsrules .= "#forward all traffic to suricata by nfqueue\n";
    #nft add rule ip ip_ips_table ips-input iif eno3 queue num 0-7 bypass
    #nft add rule ip ip_ips_table ips-input iif eno4 queue num 0-7 bypass

    #$ipsrules .= "add rule ip ip_ips_table ips-input iif \$lan queue num 0-7 bypass\n";
    #$ipsrules .= "add rule ip ip_ips_table ips-input iif \$wan queue num 0-7 bypass\n";
    #$ipsrules .= "add rule ip ip_ips_table ips-input iif lo queue num 0-7 bypass\n";
    $ipsrules .= "add rule ip ip_ips_table ips-input tcp dport !={ 8005, 6379, 3310, 8265, 8075-8077, 6666, 10002-19999, 6379, 39265, 5000, x11-6, 6789, 8089 } queue num 0-7 bypass\n";


    #nft add rule ip ip_ips_table ips-forward iif eno3 oif eno4 queue num 0-7 bypass
    #nft add rule ip ip_ips_table ips-forward iif eno4 oif eno3 queue num 0-7 bypass
    $ipsrules .= "add rule ip ip_ips_table ips-forward iif \$lan oif \$wan queue num 0-7 bypass\n";
    $ipsrules .= "add rule ip ip_ips_table ips-forward iif \$wan oif \$lan queue num 0-7 bypass\n";
    #$ipsrules .= "add rule ip ip_ips_table ips-forward iif \$lan oif lo queue num 0-7 bypass\n";
    #$ipsrules .= "add rule ip ip_ips_table ips-forward iif lo oif \$lan queue num 0-7 bypass\n";
    #$ipsrules .= "add rule ip ip_ips_table ips-forward iif \$wan oif lo queue num 0-7 bypass\n";
    #$ipsrules .= "add rule ip ip_ips_table ips-forward iif lo oif \$wan queue num 0-7 bypass\n";

    #nft add rule ip ip_ips_table ips-output oif eno3 queue num 0-7 bypass
    #nft add rule ip ip_ips_table ips-output oif eno4 queue num 0-7 bypass
    #$ipsrules .= "add rule ip ip_ips_table ips-output oif \$lan queue num 0-7 bypass\n";
    #$ipsrules .= "add rule ip ip_ips_table ips-output oif \$wan queue num 0-7 bypass\n";
    #$ipsrules .= "add rule ip ip_ips_table ips-output oif lo queue num 0-7 bypass\n";
    $ipsrules .= "add rule ip ip_ips_table ips-output tcp dport !={ 3128 } queue num 0-7 bypass\n";
    $ipsrules .= "add rule ip ip_ips_table ips-output tcp sport !={ 3128 } queue num 0-7 bypass\n";
    $ipsrules .= "add rule ip ip_ips_table ips-output udp dport !={ 53 } queue num 0-7 bypass\n";

//    $ipsrules .= "add rule ip6 ip6_ips_table ips-input queue num 3 bypass counter accept\n";
//    $ipsrules .= "add rule ip6 ip6_ips_table ips-forward queue num 3 bypass counter accept\n";
//    $ipsrules .= "add rule ip6 ip6_ips_table ips-output queue num 3 bypass counter accept\n";

    $ftp_rules = "\n# FTP rules\n";
    $ftp_rules .= "add ct helper ip ip_stateful_ftp ftp-standard {type \"ftp\" protocol tcp;}\n";
    $ftp_rules .= "#add rule ip ip_stateful_ftp pre tcp dport 21 ct helper set \"ftp-standard\"\n"; // wait for init stateful object
    $ftp_rules .= "add rule ip ip_nat prerouting ct helper \"ftp\" accept\n";
    $ftp_rules .= "add rule ip ip_stateful_ftp pre tcp dport 21 ct helper set \"ftp-standard\"\n";

    $natrules = "\n# NAT Redirects\n";
    $natrules .= "# no nat proto carp all\n";
    $natrules .= "# no rdr proto carp all\n";
//    $natrules .= "add rule ip_nat prerouting ip daddr ".$config['interfaces']['wan']['ipaddr']." tcp dport { 82} dnat to 10.0.2.10:80\n";
    $natrules .= "add rule ip_nat postrouting masquerade\n";

    // caching proxy squid - icap - clamav
//    $natrules .= "add rule ip ip_nat prerouting iif \$lan tcp dport { 80 } redirect to :3128\n";
//    $natrules .= "add rule ip ip_nat prerouting iif \$lan tcp dport { 443 } redirect to :3129\n";
    $natrules .= $fw->outputNatRules();

    if ($verbose) {
        echo '.';
        flush();
    }

    /* enable pf if we need to, otherwise disable */
    if (!isset($config['system']['disablefilter'])) {
        //mwexec("/sbin/pfctl -e", true);
        mwexec("service nftables start", true);
    } else {
        //mwexec("/sbin/pfctl -d", true);
        mwexec("service nftables stop", true);
        if ($verbose) {
            echo "done.\n";
        }
        unlock($filterlck);
        return;
    }

    if ($verbose) {
        echo '.';
        flush();
    }

    $limitrules = '';

    if (!empty($config['system']['maximumtableentries'])) {
        $limitrules .= "set limit table-entries {$config['system']['maximumtableentries']}\n";
        set_single_sysctl('net.pf.request_maxcount', $config['system']['maximumtableentries']);
    } elseif (is_bogonsv6_used()) {
        $max_table_entries = default_table_entries_size();
        $req_table_entries = 1000000;
        if ($max_table_entries <= $req_table_entries) {
            $limitrules .= "set limit table-entries {$req_table_entries}\n";
            set_single_sysctl('net.pf.request_maxcount', $req_table_entries);
        } else {
            set_single_sysctl('net.pf.request_maxcount', $max_table_entries);
        }
    }

    if (!empty($config['system']['rulesetoptimization'])) {
        $limitrules .= "set ruleset-optimization {$config['system']['rulesetoptimization']}\n";
    } else {
        $limitrules .= "set ruleset-optimization basic\n";
    }

    if ($config['system']['optimization'] != '') {
        $limitrules .= "set optimization {$config['system']['optimization']}\n";
        if ($config['system']['optimization'] == "conservative") {
            $limitrules .= "set timeout { udp.first 300, udp.single 150, udp.multiple 900 }\n";
        }
    } else {
        $limitrules .= "set optimization normal\n";
    }

    if (!empty($config['system']['adaptivestart']) && !empty($config['system']['adaptiveend'])) {
        $limitrules .= "set timeout { adaptive.start {$config['system']['adaptivestart']}, adaptive.end {$config['system']['adaptiveend']} }\n";
    } else {
        $limitrules .= "set timeout { adaptive.start 0, adaptive.end 0 }\n";
    }
    if (!empty($config['system']['state-policy'])) {
        $limitrules .= "set state-policy if-bound\n";
    }

    if (!empty($config['system']['maximumstates'])) {
        $limitrules .= "set limit states {$config['system']['maximumstates']}\n";
        $limitrules .= "set limit src-nodes {$config['system']['maximumstates']}\n";
    } else {
        $max_states = default_state_size();
        $limitrules .= "set limit states {$max_states}\n";
        $limitrules .= "set limit src-nodes {$max_states}\n";
    }
    if (!empty($config['system']['maximumfrags'])) {
        $limitrules .= "set limit frags {$config['system']['maximumfrags']}\n";
    }

    if (isset($config['system']['lb_use_sticky']) && is_numeric($config['system']['srctrack']) && ($config['system']['srctrack'] > 0)) {
        $limitrules .= "set timeout src.track {$config['system']['srctrack']}\n";
    }

    $rules = "#!/usr/sbin/nft -fnn\n";
    //$rules = "{$limitrules}\n";
    $rules .= "# Start by flushing all the rules.\n";
    $rules .= "flush ruleset\n";
    $rules .= "{$aliases} \n";
    //$rules .= filter_setup_logging_interfaces($cnfint);
    $rules .= "\n";
    //$rules .= "set skip on pfsync0\n";
    $rules .= "\n";
    //$rules .= filter_generate_scrubing($cnfint);
    $rules .= "\n";
    $rules .= "{$ipsrules}\n";
    $rules .= "\n";
    $rules .= "{$ftp_rules}\n";
    $rules .= "\n";
    $rules .= $fw->anchorToText('nat,binat,rdr', 'head');
    $rules .= "{$natrules}\n";
    $rules .= $fw->anchorToText('nat,binat,rdr', 'tail');
    $rules .= $fw->anchorToText('fw', 'head');
    $rules .= filter_rules_legacy($cnfint);
    $rules .= $fw->outputFilterRules();
    $rules .= "add rule ip ip_filter_table forward ct status dnat accept\n";

    $rules .= $fw->anchorToText('fw', 'tail');

    // Copy rules.debug to rules.debug.old
    if (file_exists('/tmp/rules.debug')) {
        @copy('/tmp/rules.debug', '/tmp/rules.debug.old');
    }

    if (!@file_put_contents('/tmp/rules.debug', $rules, LOCK_EX)) {
        log_error("WARNING: Could not write new rules!");
        unlock($filterlck);
        if ($verbose) {
            echo "failed.\n";
        }
        return;
    }

    //@file_put_contents('/tmp/rules.limits', $limitrules);
    //mwexec('/sbin/pfctl -Of /tmp/rules.limits');

    //disable translate port to service name: 80 thanh http
    //mwexec('/usr/sbin/nft -fnn');

    // enable nf ftp
    mwexec('/sbin/modprobe nf_nat_ftp');

    exec('/usr/sbin/nft -f /tmp/rules.debug 2>&1', $rules_error, $rules_loading);

    //foreach ($sched_kill_states as $label) {
    //    mwexecf('/sbin/pfctl -k label -k %s', $label);
    //}
    mwexec('/usr/sbin/conntrack -F');

    /*
     * check for a error while loading the rules file.  if an error has occurred
     * then output the contents of the error to the caller
     */
    if ($rules_loading) {
        $config_line = '';

        /* only report issues with line numbers */
        $line_error = explode(':', $rules_error[0]);
        if (isset($line_error[1]) && (string)((int)$line_error[1]) == $line_error[1] && $line_error[1] > 0) {
            $line_number = $line_error[1];
            $line_split = file('/tmp/rules.debug');
            if (is_array($line_split)) {
                $config_line = sprintf(' - ' . gettext('The line in question reads [%s]: %s'), $line_number, $line_split[$line_number - 1]);
            }
        }

        /* Brutal ugly hack but required -- PF is stuck, unwedge */
        if (strstr("$rules_error[0]", "busy")) {
            // exec('/sbin/pfctl -d; /sbin/pfctl -e; /sbin/pfctl -f /tmp/rules.debug');
            exec('service nftables stop; service nftables start; /usr/sbin/nft -f /tmp/rules.debug');
            log_error('NFT was wedged/busy and has been reset.');
            file_notice(gettext('NFT was wedged/busy and has been reset.'));
        } else {
            // exec('/sbin/pfctl -o basic -f /tmp/rules.debug.old 2>&1');
            exec('/usr/sbin/nft -f /tmp/rules.debug.old 2>&1');
        }

        log_error(sprintf('There were error(s) loading the rules: %s%s', $rules_error[0], $config_line));
        file_notice(sprintf(gettext('There were error(s) loading the rules: %s%s'), $rules_error[0], $config_line));
        unlock($filterlck);

        if ($verbose) {
            echo "failed.\n";
        }

        return;
    }

    /* set shared forwarding according to config option */
    set_single_sysctl('net.pf.share_forward', !empty($config['system']['pf_share_forward']) ? '1' : '0');
    set_single_sysctl('net.pf.share_forward6', !empty($config['system']['pf_share_forward']) ? '1' : '0');

    /*
     * If we are not using bogonsv6 then we can remove any
     * bogonsv6 table from the running pf (if the table is
     * not there, the kill is still fine).
     */
    if (!is_bogonsv6_used()) {
        // mwexec('/sbin/pfctl -t bogonsv6 -T kill');
        // mwexec('/usr/sbin/nft delete table inet bogonsv6');
    }

    if ($verbose) {
        echo '.';
        flush();
    }

    if ($verbose) {
        echo '.';
        flush();
    }

    if ($flush_states) {
        // mwexec('/sbin/pfctl -Fs');
        // mwexec('/usr/sbin/nft reset type inet table object');
    }

    if ($verbose) {
        echo '.';
        flush();
    }

    if ($load_aliases) {
        configd_run('template reload OPNsense/Filter');
        configd_run('filter refresh_aliases', true);
    }

    if ($verbose) {
        echo "done.\n";
    }

    filter_pflog_start($verbose);

    unlock($filterlck);
}

function filter_generate_scrubing(&$FilterIflist)
{
    global $config;

    $scrubrules = '';

    /* custom rules must be first */
    if (!empty($config['filter']['scrub']['rule'])) {
        foreach ($config['filter']['scrub']['rule'] as $scrub_rule) {
            if (!isset($scrub_rule['disabled'])) {
                $scrub_rule_out = "scrub";
                $scrub_rule_out .= !empty($scrub_rule['direction']) ? " " . $scrub_rule['direction'] : "";
                $scrub_rule_out .= " on ";
                $interfaces = array();
                foreach (explode(',', $scrub_rule['interface']) as $interface) {
                    if (!empty($FilterIflist[$interface]['if'])) {
                        $interfaces[] = $FilterIflist[$interface]['if'];
                    }
                }
                $scrub_rule_out .= count($interfaces) > 1 ? "{ " . implode(' ', $interfaces) . " } " : $interfaces[0];
                $scrub_rule_out .= $scrub_rule['proto'] != 'any' ? " proto " . $scrub_rule['proto'] : "";
                $scrub_rule_out .= " from ";
                if (is_alias($scrub_rule['src'])) {
                    $scrub_rule_out .= !empty($scrub_rule['srcnot']) ? "!" : "";
                    $scrub_rule_out .= '$' . $scrub_rule['src'];
                } elseif (is_ipaddr($scrub_rule['src'])) {
                    $scrub_rule_out .= !empty($scrub_rule['srcnot']) ? "!" : "";
                    $scrub_rule_out .= $scrub_rule['src'] . "/" . $scrub_rule['srcmask'];
                } else {
                    $scrub_rule_out .= "any";
                }
                $scrub_rule_out .= !empty($scrub_rule['srcport']) ?  " port " . $scrub_rule['srcport'] : "";
                $scrub_rule_out .= " to ";
                if (is_alias($scrub_rule['dst'])) {
                    $scrub_rule_out .= !empty($scrub_rule['dstnot']) ? "!" : "";
                    $scrub_rule_out .= '$' . $scrub_rule['dst'];
                } elseif (is_ipaddr($scrub_rule['dst'])) {
                    $scrub_rule_out .= !empty($scrub_rule['dstnot']) ? "!" : "";
                    $scrub_rule_out .= $scrub_rule['dst'] . "/" . $scrub_rule['dstmask'];
                } else {
                    $scrub_rule_out .= "any";
                }
                $scrub_rule_out .= !empty($scrub_rule['dstport']) ?  " port " . $scrub_rule['dstport'] : "";
                $scrub_rule_out .= !empty($scrub_rule['no-df']) ? " no-df " : "";
                $scrub_rule_out .= !empty($scrub_rule['random-id']) ? " random-id " : "";
                $scrub_rule_out .= !empty($scrub_rule['max-mss']) ? " max-mss " . $scrub_rule['max-mss'] .  " " : "";
                $scrub_rule_out .= !empty($scrub_rule['min-ttl']) ? " min-ttl " . $scrub_rule['min-ttl'] .  " " : "";
                $scrub_rule_out .= !empty($scrub_rule['set-tos']) ? " set-tos " . $scrub_rule['set-tos'] .  " " : "";
                $scrub_rule_out .= "\n";
                if (count($interfaces) == 0) {
                    # unknown interface, skip rule
                    $scrubrules .= "#";
                }
                $scrubrules .= $scrub_rule_out;
            }
        }
    }

    /* scrub per interface options */
    if (empty($config['system']['scrub_interface_disable'])) {
        foreach ($FilterIflist as $scrubcfg) {
            if (isset($scrubcfg['virtual']) || empty($scrubcfg['descr'])) {
                continue;
            }

            $mssclamp = '';
            if (
                !empty($scrubcfg['mss']) && is_numeric($scrubcfg['mss']) &&
                !in_array($scrubcfg['if'], array('pppoe', 'pptp', 'l2tp'))
            ) {
                $mssclamp = 'max-mss ' . (intval($scrubcfg['mss'] - 40));
            }

            $scrubnodf = !empty($config['system']['scrubnodf']) ? 'no-df' : '';
            $scrubrnid = !empty($config['system']['scrubrnid']) ? 'random-id' : '';
            $scrubrules .= "scrub on {$scrubcfg['if']} all {$scrubnodf} {$scrubrnid} {$mssclamp}\n";
        }
    }

    return $scrubrules;
}

function filter_generate_aliases()
{
    global $config;

    $aliases = "\n# table declaration\n";
    $aliases .= "add table ip ip_filter_table\n";
    $aliases .= "add table ip6 ip6_filter_table\n";
    $aliases .= "\n";
    $aliases .= "add table ip ip_ips_table\n";
    $aliases .= "add table ip6 ip6_ips_table\n";
    $aliases .= "\n";
    $aliases .= "add table ip ip_stateful_ftp\n";
    $aliases .= "add table ip6 ip6_stateful_ftp\n";
    $aliases .= "\n";
    $aliases .= "define sshlockout_ip = {0.0.0.1}\n";
    $aliases .= "define sshlockout_ip6 = {2000::/16}\n";
    $aliases .= "\n";
    $aliases .= "define virusprot_ip = {0.0.0.1}\n";
    $aliases .= "define virusprot_ip6 = {2000::/16}\n";

    $lan_net_ip_parts = explode('.', $config['interfaces']['lan']['ipaddr']);
    $lan_net_ip = "$lan_net_ip_parts[0].$lan_net_ip_parts[1].$lan_net_ip_parts[2].0";
    $wan_net_ip_parts = explode('.', $config['interfaces']['wan']['ipaddr']);
    $wan_net_ip = "$wan_net_ip_parts[0].$wan_net_ip_parts[1].$wan_net_ip_parts[2].0";

    $aliases .= "\n";
    $aliases .= "\n# Defining variables is easy in nftables scripts.\n";
    $aliases .= "define lan_net_ip = {".$lan_net_ip."/".$config['interfaces']['lan']['subnet']."} # la dia chi mang cua card LAN enp2s0: 10.0.2.15/24\n";
    $aliases .= "define lan_net_ip6 = {fe80::260:97ff:fe5b:732d} # la dia chi mang cua card LAN enp2s0: fe80::260:97ff:fe5b:732d\n";
    $aliases .= "\n# => nen lay dia chi ip tu cau hinh - ifconfig - thi tot, ko nen hard code\n";
    $aliases .= "define lan_address_ip = {".$config['interfaces']['lan']['ipaddr']."} # dia chi cua card lan enp2s0\n";
    $aliases .= "define lan_address_ip6 = {fe80::260:97ff:fe5b:732d} # dia chi cua card lan enp2s0\n";
    $aliases .= "define this_firewall_ip = {".$config['interfaces']['lan']['ipaddr'].", ".$config['interfaces']['wan']['ipaddr']."} # dia chi cua 2 card mang cua firewall\n";
    $aliases .= "define this_firewall_ip6 = {fe80::8a88:88ff:fe88:8788, fe80::260:97ff:fe5b:732d} # dia chi cua 2 card mang cua firewall\n";
    $aliases .= "define wan_net_ip = {".$wan_net_ip."/".$config['interfaces']['wan']['subnet']."} # la dia chi mang cua card WAN\n";
    $aliases .= "define wan_net_ip6 = {fe80::8a88:88ff:fe88:8788} # la dia chi mang cua card WAN\n";
    $aliases .= "define wan_address_ip = {".$config['interfaces']['wan']['ipaddr']."} # dia chi ip cua card WAN\n";
    $aliases .= "define wan_address_ip6 = {fe80::8a88:88ff:fe88:8788} # dia chi ip cua card WAN\n";
    $aliases .= "define lo_net_ip = {127.0.0.1/8} # dia chi ipv4 loopback\n";
    $aliases .= "define lo_net_ip6 = {::1} # dia chi ipv4 loopback\n";

    $aliases .= "add set ip ip_filter_table lan_net_ip {type ipv4_addr; elements={{$lan_net_ip}};}\n";
    $aliases .= "add set ip ip_filter_table lan_address_ip {type ipv4_addr; elements=\$lan_address_ip;}\n";
    $aliases .= "add set ip ip_filter_table this_firewall_ip {type ipv4_addr; elements=\$this_firewall_ip;}\n";
    $aliases .= "add set ip ip_filter_table wan_net_ip {type ipv4_addr; elements={{$wan_net_ip}};}\n";
    $aliases .= "add set ip ip_filter_table wan_address_ip {type ipv4_addr; elements=\$wan_address_ip;}\n";
    $aliases .= "add set ip ip_filter_table lo_net_ip {type ipv4_addr; elements={127.0.0.1};}\n";
    $aliases .= "add set ip6 ip6_filter_table lan_net_ip6 {type ipv6_addr; elements=\$lan_net_ip6;}\n";
    $aliases .= "add set ip6 ip6_filter_table lan_address_ip6 {type ipv6_addr; elements=\$lan_address_ip6;}\n";
    $aliases .= "add set ip6 ip6_filter_table this_firewall_ip6 {type ipv6_addr; elements=\$this_firewall_ip6;}\n";
    $aliases .= "add set ip6 ip6_filter_table wan_net_ip6 {type ipv6_addr; elements=\$wan_net_ip6;}\n";
    $aliases .= "add set ip6 ip6_filter_table wan_address_ip6 {type ipv6_addr; elements=\$wan_address_ip6;}\n";
    $aliases .= "add set ip6 ip6_filter_table lo_net_ip6 {type ipv6_addr; elements=\$lo_net_ip6;}\n";

    $aliases .= "\n";
    $aliases .= "# set interface names\n";
    $aliases .= "define wan = ".$config['interfaces']['wan']['if']."\n";
    $aliases .= "define lan = ".$config['interfaces']['lan']['if']."\n";
    $aliases .= "# set interface names\n";
    $aliases .= "define all_interfaces= {\$wan, \$lan}\n";
    $aliases .= "\n";
    $aliases .= "# set declaration for bogons, sshlockout table\n";
    $aliases .= "# set bogons for table <bogons> persist file \"/usr/local/etc/bogons\" in pf\n";
    $aliases .= "\n";
    $aliases .= "define bogons_ip = { 127.0.0.0/8, 169.254.0.0/16,192.0.0.0/24, 192.0.2.0/24, 198.18.0.0/15, 198.51.100.0/24, 203.0.113.0/24, 224.0.0.0/4, 240.0.0.0/4 }\n";
    if (is_bogonsv6_used()) {
        $aliases .= "define bogons_ip6 = { 2000::/16,2001:1000::/23,2001:100::/24,2001:10::/28,2001:1::/32,2001:20::/27,2001:2::/31,2001:40::/26,2001:4::/30,2001:4e00::/23,2001:6000::/19,2001:80::/25,2001:8::/29,2001:c000::/18,2001:db8::/32,2003:4000::/18,2003:8000::/17,2004::/14,2008::/13,2010::/12,2020::/11,2040::/10,2080::/9,2100::/8,2200::/7,2410::/12,2420::/11,2440::/10,2480::/9,2500::/8,2610:1000::/20,2610:2000::/19,2610:200::/23,2610:4000::/18,2610:400::/22,2610:8000::/17,2610:800::/21,2611::/16,2612::/15,2614::/14,2618::/13,2620:1000::/20,2620:2000::/19,2620:200::/23,2620:4000::/18,2620:400::/22,2620:8000::/17,2620:800::/21,2621::/16,2622::/15,2624::/14,2628::/13,2630::/12,2640::/10,2680::/9,2700::/8,2810::/12,2820::/11,2840::/10,2880::/9,2900::/8,2a10::/12,2a20::/11,2a40::/10,2a80::/9,2b00::/8,2c10::/12,2c20::/11,2c40::/10,2c80::/9,2d00::/8,2e00::/7,3000::/4,4000::/2,8000::/1,::/3}\n";
    }

    $aliases .= "\n";
    $aliases .= "# them cac chain, chain ten la \"input\", \"forward\" va \"output\"\n";
    $aliases .= "# IPV4\n";
    $aliases .= "add chain ip ip_filter_table input { type filter hook input priority 20; policy accept;}\n";
    $aliases .= "add chain ip ip_filter_table forward { type filter hook forward priority 20; policy accept;}\n";
    $aliases .= "add chain ip ip_filter_table output { type filter hook output priority 20; policy accept;}\n";
    $aliases .= "# IPV6\n";
    $aliases .= "add chain ip6 ip6_filter_table input { type filter hook input priority 30; policy accept;}\n";
    $aliases .= "add chain ip6 ip6_filter_table forward { type filter hook forward priority 30; policy accept;}\n";
    $aliases .= "add chain ip6 ip6_filter_table output { type filter hook output priority 30; policy accept;}\n";
    $aliases .= "\n";
    $aliases .= "# DAT LAI POLICY DEFAULT LA DROP \n";
    $aliases .= "# IPV4\n";
    $aliases .= "# INPUT\n";
    $aliases .= "add chain ip ip_filter_table input { policy drop;}\n";
    $aliases .= "# FORWARD\n";
    $aliases .= "add chain ip ip_filter_table forward { policy drop;}\n";
    $aliases .= "# OUTPUT\n";
    $aliases .= "add chain ip ip_filter_table output { policy drop;}\n";
    $aliases .= "\n";
    $aliases .= "# IPV6\n";
    $aliases .= "# INPUT\n";
    $aliases .= "add chain ip6 ip6_filter_table input { policy drop;}\n";
    $aliases .= "# FORWARD\n";
    $aliases .= "add chain ip6 ip6_filter_table forward { policy drop;}\n";
    $aliases .= "# OUTPUT\n";
    $aliases .= "add chain ip6 ip6_filter_table output { policy drop;}\n";

    $aliases .= "\n";
    $aliases .= "# Cau hinh IPS chain\n";
    $aliases .= "add chain ip ip_ips_table ips-input { type filter hook input priority 60; policy accept; }\n";
    $aliases .= "add chain ip ip_ips_table ips-forward { type filter hook forward priority 60; policy accept; }\n";
    $aliases .= "add chain ip ip_ips_table ips-output { type filter hook output priority 60; policy accept; }\n";
    //$aliases .= "add chain ip6 ip6_ips_table ips-input { type filter hook input priority 40; policy accept; }\n";
    //$aliases .= "add chain ip6 ip6_ips_table ips-forward { type filter hook forward priority 40; policy accept; }\n";
    //$aliases .= "add chain ip6 ip6_ips_table ips-output { type filter hook output priority 40; policy accept; }\n";
    $aliases .= "\n";

    $aliases .= "\n";
    $aliases .= "# Cau hinh FTP chain\n";
    $aliases .= "add chain ip ip_stateful_ftp pre {type filter hook prerouting priority -111;}\n";
    $aliases .= "\n";

    $aliases .= "\n";
    $aliases .= "# Cau hinh DNAT\n";
    $aliases .= "add table ip_nat\n";
    $aliases .= "add chain ip_nat prerouting { type nat hook prerouting priority -110; }\n";
    $aliases .= "add chain ip_nat postrouting { type nat hook postrouting priority 110; }\n";
    $aliases .= "\n";
    $aliases .= "add table ip6_nat\n";
    $aliases .= "add chain ip6_nat prerouting { type nat hook prerouting priority -110; }\n";
    $aliases .= "add chain ip6_nat postrouting { type nat hook postrouting priority 110; }\n";
    $aliases .= "\n";

//    $aliases .= "\n";
//    $aliases .= "# THEM CHAIN DE UU TIEN THUC HIEN CHONG LOCKOUT - ANTI LOCKOUT CHAIN AND RULE HERE \n";
//    $aliases .= "# IPV4 \n";
//    $aliases .= "add chain ip ip_filter_table input_antilockout { type filter hook input priority 4; policy accept;}\n";
//    $aliases .= "add chain ip ip_filter_table forward_antilockout { type filter hook forward priority 4; policy accept;}\n";
//    $aliases .= "add chain ip ip_filter_table output_antilockout { type filter hook output priority 4; policy accept;}\n";
//    $aliases .= "# IPV6 \n";
//    $aliases .= "add chain ip6 ip6_filter_table input_antilockout { type filter hook input priority 4; policy accept;}\n";
//    $aliases .= "add chain ip6 ip6_filter_table forward_antilockout { type filter hook forward priority 4; policy accept;}\n";
//    $aliases .= "add chain ip6 ip6_filter_table output_antilockout { type filter hook output priority 4; policy accept;}\n";
//
//    $aliases .= "\n";
//    $aliases .= "# INPUT\n";
//    $aliases .= 'add rule ip ip_filter_table input_antilockout tcp dport { http, https, ssh } accept comment "anti-lockout rule"'."\n";
//    $aliases .= 'add rule ip ip_filter_table input_antilockout tcp dport 82 accept comment "anti-lockout rule"'."\n";
//    $aliases .= 'add rule ip6 ip6_filter_table input_antilockout tcp dport { http, https, ssh } accept comment "anti-lockout rule"'."\n";
//    $aliases .= 'add rule ip6 ip6_filter_table input_antilockout tcp dport 82 accept comment "anti-lockout rule"'."\n";
//    $aliases .= "# OUTPUT\n";
//    $aliases .= 'add rule ip ip_filter_table output_antilockout ct state invalid drop comment "Drop invalid connections"'."\n";
//    $aliases .= 'add rule ip ip_filter_table output_antilockout ct state established,related log prefix "nft.accept output_antilockout state established,related_" accept'."\n";
//    $aliases .= 'add rule ip6 ip6_filter_table output_antilockout ct state invalid drop comment "Drop invalid connections"'."\n";
//    $aliases .= 'add rule ip6 ip6_filter_table output_antilockout ct state established,related log prefix "nft.accept output_antilockout state established,related_" accept'."\n";

    $aliases .= "\n";
    $aliases .= "\n";
    $aliases .= "\n# User Aliases\n";
    $aliasObject = new \OPNsense\Firewall\Alias();
    foreach ($aliasObject->aliasIterator() as $aliased) {
        if (in_array($aliased['name'], ["bogons", "bogonsv6", "sshlockout", "virusprot", "virusprot_ipv6"])) {
            continue;
        }
        switch ($aliased['type']) {
            case "urltable_ports":
            case "url_ports":
                # a bit of a hack, but prevents the ruleset from not being able to load if these types are in
                # the configuration.
                $aliases .= "{$aliased['name']} = \"{ 0 <> 65535 }\"\n";
                log_error(sprintf('URL port aliases types not supported [%s]', $aliased['name']));
                file_notice(sprintf(gettext('URL port aliases types not supported [%s]'), $aliased['name']));
                break;
            case "port":
                $tmp_ports = implode(" ", filter_core_get_port_alias($aliased['name'], array(), $aliasObject));
                $aliases .= "{$aliased['name']} = \"{ {$tmp_ports} }\"\n";
                break;
            default:
                //$tblopt = (!empty($aliased['counters']) ? 'counters' : '') . " persist ";
                // $aliases .= "define {$aliased['name']} = {}\n"; //.{$tblopt}

                //nft add set ip ip_filter_table facebook {type ipv6_addr \;}
                //nft add set ip ip6_filter_table facebook {type ipv6_addr \;}
                $aliases .= "add set ip ip_filter_table {$aliased['name']} {type ipv4_addr;}\n"; //.{$tblopt}
                $aliases .= "add set ip6 ip6_filter_table {$aliased['name']} {type ipv6_addr;}\n"; //.{$tblopt}
                break;
        }
    }

    return $aliases;
}

function filter_rules_legacy(&$FilterIflist)
{
    global $config;
    $log = array();
    $log['block'] = !isset($config['syslog']['nologdefaultblock']) ? "log" : "";

    $ipfrules = "";
    $isbridged = false;
    if (isset($config['bridges']['bridged'])) {
        foreach ($config['bridges']['bridged'] as $oc2) {
            if (stristr($oc2['members'], $on)) {
                $isbridged = true;
                break;
            }
        }
    }
    foreach ($FilterIflist as $on => $oc) {
        if (!$isbridged && !isset($oc['internal_dynamic']) && $oc['if'] != 'lo') {
            //todo add antispoof rule
            $ipfrules .= "# antispoof {$log['block']} for {$oc['if']} \n";
        }
    }
    return $ipfrules;
}

/****f* filter/filter_get_time_based_rule_status
 * NAME
 *   filter_get_time_based_rule_status
 * INPUTS
 *   xml schedule block
 * RESULT
 *   true/false - true if the rule should be installed
 ******/
/*
 <schedules>
   <schedule>
     <name>ScheduleMultipleTime</name>
     <descr>main descr</descr>
     <time>
       <position>0,1,2</position>
       <hour>0:0-24:0</hour>
       <desc>time range 2</desc>
     </time>
     <time>
       <position>4,5,6</position>
       <hour>0:0-24:0</hour>
       <desc>time range 1</desc>
     </time>
   </schedule>
 </schedules>
*/
function filter_get_time_based_rule_status($schedule)
{
    /* no schedule? rule should be installed */
    if (empty($schedule)) {
        return true;
    }
    /*
     * iterate through time blocks and determine
     * if the rule should be installed or not.
     */
    foreach ($schedule['timerange'] as $timeday) {
        if (empty($timeday['month'])) {
            $monthstatus = true;
        } else {
            $monthstatus = filter_tdr_month($timeday['month']);
        }
        if (empty($timeday['day'])) {
            $daystatus = true;
        } else {
            $daystatus = filter_tdr_day($timeday['day']);
        }
        if (empty($timeday['hour'])) {
            $hourstatus = true;
        } else {
            $hourstatus = filter_tdr_hour($timeday['hour']);
        }
        if (empty($timeday['position'])) {
            $positionstatus = true;
        } else {
            $positionstatus = filter_tdr_position($timeday['position']);
        }

        if ($monthstatus == true && $daystatus == true && $positionstatus == true && $hourstatus == true) {
            return true;
        }
    }
    return false;
}

function filter_tdr_day($schedule)
{
    /*
     * Calculate day of month.
     * IE: 29th of may
     */
    $date = date("d");
    $defined_days = explode(",", $schedule);
    foreach ($defined_days as $dd) {
        if ($date == $dd) {
            return true;
        }
    }
    return false;
}

function filter_tdr_hour($schedule)
{
    /* $schedule should be a string such as 16:00-19:00 */
    $tmp = explode("-", $schedule);
    $starting_time = strtotime($tmp[0]);
    $ending_time = strtotime($tmp[1]);
    $now = strtotime("now");
    if ($now >= $starting_time && $now < $ending_time) {
        return true;
    }
    return false;
}

function filter_tdr_position($schedule)
{
    /*
     * Calculate position, ie: day of week.
     * Sunday = 7, Monday = 1, Tuesday = 2
     * Weds = 3, Thursday = 4, Friday = 5,
     * Saturday = 6
     * ...
     */
    $weekday = date("w");
    if ($weekday == 0) {
        $weekday = 7;
    }
    $schedule_days = explode(",", $schedule);
    foreach ($schedule_days as $day) {
        if ($day == $weekday) {
            return true;
        }
    }
    return false;
}

function filter_tdr_month($schedule)
{
    /*
     * Calculate month
     */
    $todays_month = date("n");
    $months = explode(",", $schedule);
    foreach ($months as $month) {
        if ($month == $todays_month) {
            return true;
        }
    }
    return false;
}

function filter_setup_logging_interfaces(&$FilterIflist)
{
    $rules = '';

    if (isset($FilterIflist['lan'])) {
        $rules .= "set loginterface {$FilterIflist['lan']['if']}\n";
    } elseif (isset($FilterIflist['wan'])) {
        $rules .= "set loginterface {$FilterIflist['wan']['if']}\n";
    }

    return $rules;
}

function default_table_entries_size()
{
    $current = `pfctl -sm | grep table-entries | awk '{print $4};'`;

    return $current;
}

function default_state_size()
{
    /* get system memory amount */
    $memory = get_memory();
    $physmem = $memory[0];

    /* Be cautious and only allocate 10% of system memory to the state table */
    $max_states = (int) ($physmem / 10) * 1000;

    return $max_states;
}

function get_protocols()
{
    $protocols = array('any', 'TCP', 'UDP', 'TCP/UDP', 'ICMP', 'ESP', 'AH', 'GRE', 'IGMP', 'PIM', 'OSPF');

    /* IPv6 extension headers are skipped by the packet filter, we cannot police them */
    $ipv6_ext = array('IPV6-ROUTE', 'IPV6-FRAG', 'IPV6-OPTS', 'IPV6-NONXT', 'MOBILITY-HEADER');

    foreach (explode("\n", file_get_contents('/etc/protocols')) as $line) {
        if (substr($line, 0, 1) != "#") {
            $parts = preg_split('/\s+/', $line);
            if (count($parts) >= 4 && $parts[1] > 0) {
                $protocol = trim(strtoupper($parts[0]));
                if (!in_array($protocol, $ipv6_ext) && !in_array($protocol, $protocols)) {
                    $protocols[] = $protocol;
                }
            }
        }
    }
    return $protocols;
}
