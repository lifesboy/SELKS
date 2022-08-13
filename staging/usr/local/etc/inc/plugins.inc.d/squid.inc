<?php

/*
 * Copyright (C) 2016 Deciso B.V.
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

function squid_enabled()
{
    global $config;

    return isset($config['OPNsense']['proxy']['general']['enabled'])
        && $config['OPNsense']['proxy']['general']['enabled'] == 1;
}

function squid_services()
{
    global $config;

    $services = array();

    if (
        isset($config['OPNsense']['proxy']['general']['enabled']) &&
        $config['OPNsense']['proxy']['general']['enabled'] == 1
    ) {
        $services[] = array(
            'description' => gettext('Web Proxy'),
            'configd' => array(
                'restart' => array('proxy restart'),
                'start' => array('proxy start'),
                'stop' => array('proxy stop'),
            ),
            'pidfile' => '/var/run/squid.pid',
            'name' => 'squid',
        );
    }

    return $services;
}

function squid_xmlrpc_sync()
{
    $result = array();

    $result[] = array(
        'description' => gettext('Web Proxy'),
        'section' => 'OPNsense.proxy',
        'id' => 'squid',
    );

    return $result;
}

/**
 * our squid instance by default logs to file, when syslog is selected, we need a target definition to catch traffic.
 * which flushes our local traffic to /var/log/squid.log (which would otherwise end up in /var/log/squid/access.log)
 */
function squid_syslog()
{
    $logfacilities = array();
    $logfacilities['squid'] = array(
        'facility' => array('(squid-1)')
    );
    return $logfacilities;
}

function squid_configure()
{
    return array(
        'bootup' => array('squid_configure_defer'),
        'local' => array('squid_configure_start'),
        'newwanip' => array('squid_configure_defer'),
    );
}


function squid_configure_start($verbose = false)
{
    squid_configure_do($verbose, true);
}

function squid_configure_defer($verbose = false)
{
    squid_configure_do($verbose, false);
}

function squid_configure_do($verbose = false, $start_squid = true)
{
    if ($start_squid) {
        killbypid('/var/run/squid.pid', 'TERM', true);
    }

    if (!squid_enabled()) {
        return;
    }

    if ($verbose) {
        echo 'Starting squid service...';
        flush();
    }

    configd_run('proxy start');

    if ($verbose) {
        echo "done.\n";
    }
}