#!/bin/sh
### BEGIN INIT INFO
# Provides:          configd
# Required-Start:    $local_fs $remote_fs $network $syslog
# Required-Stop:     $local_fs $remote_fs $network $syslog
# Should-Start:      fam
# Should-Stop:       fam
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Start the configd daemon service backend.
# Description:       Opnsense config daemon service backend
### END INIT INFO

PATH=/sbin:/bin:/usr/sbin:/usr/bin
DAEMON=/usr/local/opnsense/service/configd.py
NAME=configd
DESC="Opnsense config daemon service backend"
PIDFILE=/var/run/$NAME.pid
SCRIPTNAME=/etc/init.d/$NAME

DAEMON_OPTS=""

#test -x $DAEMON || exit 0

. /etc/rc.subr
name=$NAME
desc=$DESC

set -e


configd_load_rc_config()
{
	required_args=""
	required_dirs="/usr/local/opnsense/service/"
	required_files=""
	command_args="${required_args}"
	command=/usr/local/opnsense/service/configd.py
	command_interpreter=/usr/local/bin/python3
}

#
configd_prestart()
{
	# reset access rights on configd daemon script
	chmod 700 /usr/local/opnsense/service/configd.py
}

#
configd_poststart()
{
	# give the daemon some time to initialize its configuration
	sleep 1
}

# kill configd
configd_stop()
{
	if [ -z "$rc_pid" ]; then
		[ -n "$rc_fast" ] && return 0
		_run_rc_notrunning
		return 1
	fi

	echo -n "Stopping ${name}."
	# first ask gently to exit
	kill -15 ${rc_pid}

	# wait max 2 seconds for gentle exit
	for i in $(seq 1 20);
	do
		if [ -z "`/bin/ps -ex | /usr/bin/awk '{print $1;}' | /usr/bin/grep "^${rc_pid}"`" ]; then
			break
		fi
		sleep 0.1
	done

	# kill any remaining configd processes (if still running)
	for configd_pid in `/bin/ps -ex | grep 'configd.py' | /usr/bin/awk '{print $1;}' `
	do
	   kill -9 $configd_pid >/dev/null 2>&1
	done

	echo  "..done"
}

# cleanup after stopping configd
configd_poststop()
{
	if  [ -S /var/run/configd.socket ]; then
		rm /var/run/configd.socket
	fi
}

check_syntax()
{
    #$DAEMON -tt $DAEMON_OPTS > /dev/null || exit $?
    echo $DAEMON
    echo $DAEMON_OPTS
}

. /lib/lsb/init-functions

case "$1" in
    start)
        check_syntax
        log_daemon_msg "Starting $DESC" $NAME
        configd_load_rc_config
        configd_prestart
        if ! start-stop-daemon --start --oknodo --quiet \
            --pidfile $PIDFILE --exec $DAEMON -- $DAEMON_OPTS
        then
            log_end_msg 1
        else
            configd_poststart
            log_end_msg 0
        fi
        ;;
    stop)
        log_daemon_msg "Stopping $DESC" $NAME
        if start-stop-daemon --stop --retry 30 --oknodo --quiet \
            --pidfile $PIDFILE --exec $DAEMON
        then
            configd_stop
            configd_poststop
            rm -f $PIDFILE
            log_end_msg 0
        else
            log_end_msg 1
        fi
        ;;
    reload|force-reload)
        check_syntax
        log_daemon_msg "Reloading $DESC configuration" $NAME
        if start-stop-daemon --stop --signal INT --quiet \
            --pidfile $PIDFILE --exec $DAEMON \
            --retry=TERM/60/KILL/5
        then
            rm $PIDFILE
            if start-stop-daemon --start --quiet  \
                --pidfile $PIDFILE --exec $DAEMON -- $DAEMON_OPTS ; then
                log_end_msg 0
            else
                log_end_msg 1
            fi
        else
            log_end_msg 1
        fi
        ;;
    reopen-logs)
        log_daemon_msg "Reopening $DESC logs" $NAME
        if start-stop-daemon --stop --signal HUP --oknodo --quiet \
            --pidfile $PIDFILE --exec $DAEMON
        then
            log_end_msg 0
        else
            log_end_msg 1
        fi
        ;;
    restart)
        check_syntax
        $0 stop
        $0 start
        ;;
    configtest|testconfig)
        check_syntax
        ;;
    status)
        status_of_proc -p "$PIDFILE" "$DAEMON" configd && exit 0 || exit $?
        ;;
    *)
        echo "Usage: $SCRIPTNAME {start|stop|restart|reload|force-reload|reopen-logs|configtest|status}" >&2
        exit 1
        ;;
esac

exit 0
