#!/bin/sh
# this file was auto-generated, do not edit
if [ -z "${1}" ]; then
    echo "Nothing to do."
    exit 0
fi
if [ -n "${2}" ]; then
    echo ${2} > /tmp/${1}_routerv6
    echo ${2} > /tmp/${1}_defaultgwv6
fi
if [ -f /var/run/dhcp6c.pid ]; then
    if ! /bin/pkill -0 -F /var/run/dhcp6c.pid; then
        rm -f /var/run/dhcp6c.pid
    fi
fi
if [ -f /var/run/dhcp6c.pid ]; then
    /usr/bin/logger -t dhcp6c "RTSOLD script - Sending SIGHUP to dhcp6c"
    /bin/pkill -HUP -F /var/run/dhcp6c.pid
else
    /usr/bin/logger -t dhcp6c "RTSOLD script - Starting dhcp6 client"
    /usr/local/sbin/dhcp6c -c '/var/etc/dhcp6c.conf' -p '/var/run/dhcp6c.pid' -d
fi
