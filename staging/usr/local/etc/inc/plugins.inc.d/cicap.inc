<?php

/*
    Copyright (C) 2017 Michael Muenz <m.muenz@gmail.com>
    All rights reserved.

    Redistribution and use in source and binary forms, with or without
    modification, are permitted provided that the following conditions are met:

    1. Redistributions of source code must retain the above copyright notice,
       this list of conditions and the following disclaimer.

    2. Redistributions in binary form must reproduce the above copyright
       notice, this list of conditions and the following disclaimer in the
       documentation and/or other materials provided with the distribution.

    THIS SOFTWARE IS PROVIDED ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES,
    INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY
    AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
    AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
    OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
    SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
    INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
    CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
    ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
    POSSIBILITY OF SUCH DAMAGE.
*/

function cicap_enabled()
{
    global $config;

    return isset($config['OPNsense']['cicap']['general']['enabled'])
        && $config['OPNsense']['cicap']['general']['enabled'] == 1;
}

function cicap_services()
{
    global $config;

    $services = array();

    if (
        isset($config['OPNsense']['cicap']['general']['enabled']) &&
        $config['OPNsense']['cicap']['general']['enabled'] == 1
    ) {
        $services[] = array(
            'description' => gettext('C-ICAP server'),
            'configd' => array(
                'restart' => array('cicap restart'),
                //'start' => array('cicap start'),
                'start' => array('cicap restart'), // force restart when cicap is already running out of control
                'stop' => array('cicap stop'),
            ),
            'name' => 'cicap',
            // 'pidfile' => '/var/run/c-icap/c-icap.pid'
            'script' => '/usr/local/c-icap/bin/c-icap'
        );
    }

    return $services;
}

function cicap_configure()
{
    return array(
        'bootup' => array('cicap_configure_defer'),
        'local' => array('cicap_configure_start'),
        'newwanip' => array('cicap_configure_defer'),
    );
}


function cicap_configure_start($verbose = false)
{
    cicap_configure_do($verbose, true);
}

function cicap_configure_defer($verbose = false)
{
    cicap_configure_do($verbose, false);
}

function cicap_configure_do($verbose = false, $start_cicap = true)
{
    if ($start_cicap) {
        // killbypid('/var/run/c-icap/c-icap.pid', 'TERM', true);
        $pids = getpids('/usr/local/c-icap/bin/c-icap');
        array_map(function ($pid) {
            killbypid($pid, 'TERM', true);
        }, is_array($pids) ? $pids : []);
    }

    if (!cicap_enabled()) {
        return;
    }

    if ($verbose) {
        echo 'Starting cicap service...';
        flush();
    }

    configd_run('cicap restart');

    if ($verbose) {
        echo "done.\n";
    }
}