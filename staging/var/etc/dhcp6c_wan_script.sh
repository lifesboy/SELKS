#!/bin/sh
if [ -n 'debug' ]; then
	/usr/bin/logger -t dhcp6c "dhcp6c $REASON on em2"
fi
case $REASON in
REQUEST)
	if [ -n "${PDINFO}" ]; then
		echo ${PDINFO} > /tmp/em2_pdinfo
	fi
	/usr/bin/logger -t dhcp6c "dhcp6c $REASON on em2 - running newipv6"
	/usr/local/opnsense/service/configd_ctl.py interface newipv6 em2
	;;
EXIT|RELEASE)
	/usr/bin/logger -t dhcp6c "dhcp6c $REASON on em2 - running newipv6"
	rm -f /tmp/em2_pdinfo
	/usr/local/opnsense/service/configd_ctl.py interface newipv6 em2
	;;
*)
	;;
esac
