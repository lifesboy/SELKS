#!/bin/sh
### BEGIN INIT INFO
# Provides:          captiveportal
# Required-Start:    $local_fs $remote_fs $network $syslog
# Required-Stop:     $local_fs $remote_fs $network $syslog
# Should-Start:      fam
# Should-Stop:       fam
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Start the captiveportal daemon service backend.
# Description:       Opnsense captive portal daemon service backend
### END INIT INFO

PATH=/sbin:/bin:/usr/sbin:/usr/bin
DAEMON=/usr/local/opnsense/scripts/OPNsense/CaptivePortal/cp-background-process.py
NAME=captiveportal
DESC="Opnsense captive portal daemon service backend"
PIDFILE=/var/run/$NAME.pid
SCRIPTNAME=/etc/init.d/$NAME

DAEMON_OPTS=""

#test -x $DAEMON || exit 0

. /lib/lsb/init-functions

name=$NAME
pidfile=$PIDFILE
desc=$DESC

. /etc/rc.subr

set -e


rcvar=captiveportal_enable

[ -z "$captiveportal_enable" ]       && captiveportal_enable="NO"

captiveportal_load_rc_config()
{
    CPWORKDIR="/var/captiveportal"
    CPDEFAULTTEMPLATE="/usr/local/opnsense/scripts/OPNsense/CaptivePortal/htdocs_default"

    # extract all zones from captive portal configuration
    CPZONES=`cat /usr/local/etc/captiveportal.conf | grep "\[zone_" | sed 's/\[zone_//' | sed 's/\]//'`
}

captiveportal_cleanup_zones()
{
    # cleanup removed zones
    for installed_zoneid in `ls $CPWORKDIR |  sed 's/zone//g'`; do
        if [ -d $CPWORKDIR/zone$installed_zoneid ]; then
            is_installed=0
            for zoneid in $CPZONES; do
                if [ "$zoneid" -eq "$installed_zoneid" ]; then
                    is_installed=1
                fi
            done
            if [ "$is_installed" -eq 0 ]; then
                echo "Uninstall : zone $installed_zoneid"
                umount "$CPWORKDIR/zone$installed_zoneid/dev"
                rm -rf "$CPWORKDIR/zone$installed_zoneid"
            fi
        fi
    done
}

captiveportal_prestart()
{
    # initialize captiveportal work directory
    mkdir -p $CPWORKDIR
}

captiveportal_start()
{
    # if the API dispatcher is already running, we will assume all parts are running
    if ! pgrep -qF /var/run/lighttpd-api-dispatcher.pid 2> /dev/null; then
        echo "Starting API dispatcher"
        /usr/sbin/lighttpd -f /var/etc/lighttpd-api-dispatcher.conf

        log_daemon_msg "Checkpoint 1"
        # generate ssl certificates
        /usr/local/opnsense/scripts/OPNsense/CaptivePortal/generate_certs.php

        # startup / bootstrap zones
        for zoneid in $CPZONES; do
            # bootstrap captiveportal jail
            zonedirname="zone$zoneid"
            echo "Install : zone $zoneid"
            mkdir -p $CPWORKDIR/$zonedirname
            # remove temp (flush)
            rm -rf $CPWORKDIR/$zonedirname/tmp
            mkdir -p $CPWORKDIR/$zonedirname/tmp
            chmod 770 $CPWORKDIR/$zonedirname/tmp

            mkdir -p $CPWORKDIR/$zonedirname/dev
            if ! mount -uw $CPWORKDIR/$zonedirname/dev 2> /dev/null; then
                mount -t devfs devfs $CPWORKDIR/$zonedirname/dev
            fi

            # sync default template
            cp -a $CPDEFAULTTEMPLATE/ $CPWORKDIR/$zonedirname/htdocs/

            # chown zone files to chroot user
            chown -R www:www $CPWORKDIR/$zonedirname

            # overlay custom user layout if available.
            /usr/local/opnsense/scripts/OPNsense/CaptivePortal/overlay_template.py $zoneid

            # start new instance
            echo "Start : zone $zoneid"
            /usr/sbin/lighttpd -f /var/etc/lighttpd-cp-zone-$zoneid.conf
        done

        captiveportal_cleanup_zones
        echo "start captiveportal background process"
        /usr/local/opnsense/scripts/OPNsense/CaptivePortal/cp-background-process.py start
    else
        echo "already running"
    fi
}

# stop captive portal (sub) processes
captiveportal_stop()
{
    # startup API dispatcher, forwards captive portal api request to shared OPNsense API
    if [ -f /var/run/lighttpd-api-dispatcher.pid ]; then
        echo "Stopping API dispatcher"
        /bin/pkill -TERM -F /var/run/lighttpd-api-dispatcher.pid
        if [ -f /var/run/lighttpd-api-dispatcher.pid ]; then
            # in case pkill didn't do anything, always remove pid file
            rm /var/run/lighttpd-api-dispatcher.pid
        fi
    fi

    # stopping zone http servers
    for zoneid in $CPZONES; do
        # stop running instance
        zonepid="/var/run/lighttpd-cp-zone-$zoneid.pid"
        if [ -f $zonepid ]; then
            echo "Stop : zone $zoneid"
            /bin/pkill -TERM -F $zonepid
            rm $zonepid
        fi
    done

    # stopping unconfigured zones (not in $CPZONES list)
    for zonepid in `ls /var/run/lighttpd-cp-zone-*.pid 2>/dev/null`; do
        /bin/pkill -TERM -F $zonepid
        rm $zonepid
    done

    if [ -f /var/run/captiveportal.db.pid ]; then
        echo "stop captiveportal background process"
        /bin/pkill -TERM -F /var/run/captiveportal.db.pid
    fi

    captiveportal_cleanup_zones
}


check_syntax()
{
    #$DAEMON -tt $DAEMON_OPTS > /dev/null || exit $?
    echo $DAEMON
    echo $DAEMON_OPTS
}

case "$1" in
    start)
        check_syntax
        log_daemon_msg "Starting $DESC" $NAME
        captiveportal_load_rc_config
        captiveportal_prestart
        if ! start-stop-daemon --start --oknodo --quiet \
            --make-pidfile --pidfile $PIDFILE --exec $DAEMON -- $DAEMON_OPTS
        then
            log_end_msg 1
        else
            captiveportal_start
            log_end_msg 0
        fi
        ;;
    stop)
        log_daemon_msg "Stopping $DESC" $NAME
        if start-stop-daemon --stop --retry 30 --oknodo --quiet \
            --pidfile $PIDFILE --exec $DAEMON
        then
            captiveportal_stop
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
        status_of_proc -p "$PIDFILE" "$DAEMON" captiveportal && exit 0 || exit $?
        ;;
    *)
        echo "Usage: $SCRIPTNAME {start|stop|restart|reload|force-reload|reopen-logs|configtest|status}" >&2
        exit 1
        ;;
esac

exit 0
