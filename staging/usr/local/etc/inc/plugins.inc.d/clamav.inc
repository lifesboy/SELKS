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

function clamav_enabled()
{
    global $config;

    return isset($config['OPNsense']['clamav']['general']['enabled'])
        && $config['OPNsense']['clamav']['general']['enabled'] == 1;
}

function clamav_services()
{
    global $config;

    $services = array();

    if (
        isset($config['OPNsense']['clamav']['general']['enabled']) &&
        $config['OPNsense']['clamav']['general']['enabled'] == 1
    ) {
        $services[] = array(
            'description' => gettext('ClamAV Daemon'),
            'configd' => array(
                'restart' => array('clamav restart'),
                //'start' => array('clamav start'),
                'start' => array('clamav restart'), // force restart when clamav is already running out of control
                'stop' => array('clamav stop'),
            ),
            'name' => 'clamd',
            // 'pidfile' => '/var/run/clamav/clamd.pid',
            'script' => '/usr/sbin/clamd'
        );
    }

    if (
        isset($config['OPNsense']['clamav']['general']['fc_enabled']) &&
        $config['OPNsense']['clamav']['general']['fc_enabled'] == 1
    ) {
        $services[] = array(
            'description' => gettext('freshclam daemon'),
            'configd' => array(
                'restart' => array('clamav restart'),
                //'start' => array('clamav start'),
                'start' => array('clamav restart'), // force restart when clamav is already running out of control
                'stop' => array('clamav stop'),
            ),
            'name' => 'freshclam',
            // 'pidfile' => '/var/run/clamav/freshclam.pid',
            'script' => '/usr/bin/freshclam'
        );
    }

    return $services;
}


function clamav_configure()
{
    return array(
        'bootup' => array('clamav_configure_defer'),
        'local' => array('clamav_configure_start'),
        'newwanip' => array('clamav_configure_defer'),
    );
}


function clamav_configure_start($verbose = false)
{
    clamav_configure_do($verbose, true);
}

function clamav_configure_defer($verbose = false)
{
    clamav_configure_do($verbose, false);
}

function clamav_configure_do($verbose = false, $start_clamav = true)
{
    if ($start_clamav) {
        // killbypid('/var/run/c-icap/c-icap.pid', 'TERM', true);
        $pids = getpids('/usr/sbin/clamd');
        array_map(function ($pid) {
            killbypid($pid, 'TERM', true);
        }, is_array($pids) ? $pids : []);

        $pids = getpids('/usr/bin/freshclam');
        array_map(function ($pid) {
            killbypid($pid, 'TERM', true);
        }, is_array($pids) ? $pids : []);
    }

    if (!clamav_enabled()) {
        return;
    }

    if ($verbose) {
        echo 'Starting clamav service...';
        flush();
    }

    configd_run('clamav restart');

    if ($verbose) {
        echo "done.\n";
    }
}