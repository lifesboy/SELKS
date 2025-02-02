#!/bin/sh

SURICATA_DIRS="/var/log/suricata"

for SURICATA_DIR in ${SURICATA_DIRS}; do
	mkdir -p ${SURICATA_DIR}
	chown -R logstash:logstash ${SURICATA_DIR}
	chmod -R 0755 ${SURICATA_DIR}
done

# make sure we can load our yaml file if we don't have rules installed yet
touch /etc/suricata/installed_rules.yaml
