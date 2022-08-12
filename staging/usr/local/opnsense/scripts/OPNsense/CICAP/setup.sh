#!/bin/sh

mkdir -p /var/run/c-icap
chown -R root:root /var/run/c-icap
chmod 750 /var/run/c-icap

mkdir -p /var/log/c-icap
chown -R root:root /var/log/c-icap
chmod 755 /var/log/c-icap
(cd /var/log && ln -sf c-icap cicap)
chown -R root:root /var/log/cicap

mkdir -p /tmp/c-icap/templates/virus_scan/en
chmod -R 755 /tmp/c-icap/
