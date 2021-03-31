apt install lighttpd php-fpm php
systemctl start lighttpd
systemctl enable lighttpd
systemctl status lighttpd

lighttpd-enable-mod fastcgi
lighttpd-enable-mod fastcgi-php
service lighttpd force-reload