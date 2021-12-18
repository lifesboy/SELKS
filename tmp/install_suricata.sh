apt remove --purge rustc
apt-get install curl
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env
cargo install --force cbindgen
apt-get install libpcre3 libpcre3-dbg libpcre3-dev build-essential libpcap-dev libnet1-dev libyaml-0-2 libyaml-dev pkg-config zlib1g zlib1g-dev libcap-ng-dev libcap-ng0 make libmagic-dev libnss3-dev libgeoip-dev liblua5.1-dev libhiredis-dev libevent-dev python-yaml liblz4-dev


cargo install --force --debug


git clone https://github.com/OISF/suricata.git
cd suricata/
git checkout master-6.0.x
git clone https://github.com/OISF/libhtp


#cd suricata-update
#$ curl -L https://github.com/OISF/suricata-update/archive/master.tar.gz | tar zxvf - --strip-components=1


./configure --enable-nfqueue --sysconfdir=/etc --localstatedir=/var --prefix=/usr/ --enable-lua
 --enable-rules
 --enable-rust
 #--enable-suricata-update
make
make install-full
ldconfig /usr/local/lib
ldconfig /usr/lib

/usr/bin/suricata -c /etc/suricata/suricata.yaml --pidfile /var/run/suricata.pid -q 3 -q 4 -q 5 -D -v --user=logstash


make clean
make uninstall


========
suricata --build-info
ldd /usr/bin/suricata
        linux-vdso.so.1 (0x00007ffcb19d3000)
        liblua5.1.so.0 => /lib/x86_64-linux-gnu/liblua5.1.so.0 (0x00007f3a45017000)
        libhtp.so.2 => /lib/x86_64-linux-gnu/libhtp.so.2 (0x00007f3a44fee000)
        libdl.so.2 => /lib/x86_64-linux-gnu/libdl.so.2 (0x00007f3a44fe9000)
        librt.so.1 => /lib/x86_64-linux-gnu/librt.so.1 (0x00007f3a44fdf000)
        libm.so.6 => /lib/x86_64-linux-gnu/libm.so.6 (0x00007f3a44e5c000)
        liblz4.so.1 => /lib/x86_64-linux-gnu/liblz4.so.1 (0x00007f3a44e3d000)
        libmagic.so.1 => /lib/x86_64-linux-gnu/libmagic.so.1 (0x00007f3a44e14000)
        libcap-ng.so.0 => /lib/x86_64-linux-gnu/libcap-ng.so.0 (0x00007f3a44e0c000)
        libpcap.so.0.8 => /lib/x86_64-linux-gnu/libpcap.so.0.8 (0x00007f3a44bca000)
        libnet.so.1 => /lib/x86_64-linux-gnu/libnet.so.1 (0x00007f3a449b0000)
        libnetfilter_queue.so.1 => /lib/x86_64-linux-gnu/libnetfilter_queue.so.1 (0x00007f3a449a7000)
        libnfnetlink.so.0 => /lib/x86_64-linux-gnu/libnfnetlink.so.0 (0x00007f3a447a0000)
        libjansson.so.4 => /lib/x86_64-linux-gnu/libjansson.so.4 (0x00007f3a4478f000)
        libpthread.so.0 => /lib/x86_64-linux-gnu/libpthread.so.0 (0x00007f3a4476e000)
        libyaml-0.so.2 => /lib/x86_64-linux-gnu/libyaml-0.so.2 (0x00007f3a44550000)
        libpcre.so.3 => /lib/x86_64-linux-gnu/libpcre.so.3 (0x00007f3a444dc000)
        libz.so.1 => /lib/x86_64-linux-gnu/libz.so.1 (0x00007f3a442be000)
        libnss3.so => /lib/x86_64-linux-gnu/libnss3.so (0x00007f3a44170000)
        libnssutil3.so => /lib/x86_64-linux-gnu/libnssutil3.so (0x00007f3a4413c000)
        libsmime3.so => /lib/x86_64-linux-gnu/libsmime3.so (0x00007f3a4410d000)
        libssl3.so => /lib/x86_64-linux-gnu/libssl3.so (0x00007f3a440b4000)
        libplds4.so => /lib/x86_64-linux-gnu/libplds4.so (0x00007f3a440af000)
        libplc4.so => /lib/x86_64-linux-gnu/libplc4.so (0x00007f3a440a8000)
        libnspr4.so => /lib/x86_64-linux-gnu/libnspr4.so (0x00007f3a44067000)
        libgcc_s.so.1 => /lib/x86_64-linux-gnu/libgcc_s.so.1 (0x00007f3a4404b000)
        libc.so.6 => /lib/x86_64-linux-gnu/libc.so.6 (0x00007f3a43e8a000)
        /lib64/ld-linux-x86-64.so.2 (0x00007f3a4584f000)
        libmnl.so.0 => /lib/x86_64-linux-gnu/libmnl.so.0 (0x00007f3a43c83000)