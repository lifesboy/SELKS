Build a SELKS ISO
=================

You can download the latest SELKS ready to use `from here <https://www.stamus-networks.com/open-source/>`_. However if you would like to build SELKS from scratch and/or customize and modify it - you can follow this guide bellow.

Prerequisite
------------

**NOTE:**
You can build SELKS from scratch with a choice of a OS distribution based on one of the below:

* Debian Buster

You need a Debian Buster with a decent Internet access. Building a SELKS ISO will require the download of a complete system. You will also need around 5 GB of space in the build directory.

Get the sources and prepare the system
--------------------------------------

::

 git clone https://github.com/StamusNetworks/SELKS.git
 cd SELKS

Virtualbox: do not build on mount volume

::

    apt install build-essential dkms linux-headers-$(uname -r)

Install the dependencies: ::

    cat >> /etc/apt/sources.list

    deb http://deb.debian.org/debian stretch main contrib non-free
    deb http://deb.debian.org/debian-security/ stretch/updates main contrib non-free
    deb http://deb.debian.org/debian stretch-updates main contrib non-free
    ### backports###
    deb http://ftp.debian.org/debian stretch-backports main contrib non-free

Install kernel: ::

    apt update
    apt -t stretch-backports install firmware-linux

dos2unix install-deps.sh
dos2unix build-debian-live.sh

 ./install-deps.sh

 if error not found "chroot", run with sudo (debian 10): sudo ./install-deps.sh


Build the system
----------------
Build linux image: ::

    mkdir live-default && cd live-default
    lb config
    lb build

You can now start the build: ::

 ./build-debian-live.sh

Please note, that the previous command can take up to 40 min to complete.
You will then find the ISO file under ``Stamus-Live-Build/SELKS.iso``

usage: ./build-debian-live.sh options

SELKS build your own ISO options: ::

 RUN ON DEBIAN BUSTER ONLY
 OPTIONS:
   -h      Help info
   -g      GUI option - can be "no-desktop"
   -p      Add package(s) to the build - can be one-package or "package1 package2 package3...." (should be confined to up to 10 packages)
   -k      Kernel option - can be the stable standard version of the kernel you wish to deploy -
           aka you can choose any kernel "4.x.x"  or "5.x.x" you want.
           Example: "5.4" or "5.7" or "4.19.128"


           More info on kernel versions and support:
           https://www.kernel.org/
           https://www.kernel.org/category/releases.html

   By default no options are required. The options presented here are if you wish to enable/disable/add components.
   By default SELKS will be build with a standard Debian Buster 64 bit distro and kernel ver 4.19.x respectively.

EXAMPLE (default):
******************

::

 ./build-debian-live.sh

The example above (is the default) will build a SELKS standard Debian Buster 64 bit distro - see ``Get source from git``

EXAMPLE (customizations):
*************************

::

 ./build-debian-live.sh -k 5.4.46

The example above will build a SELKS Debian 64 bit distro with kernel ver 5.4.46

::

 ./build-debian-live.sh -k 5.7.2 -p one-package

The example above will build a SELKS Debian 64 bit distro with kernel ver 5.7.2
and add the extra package named  "one-package" to the build.

::

 ./build-debian-live.sh -k 5.6.18 -g no-desktop -p one-package

The example above will build a SELKS Debian 64 bit distro, no desktop with kernel ver 5.6.18
and add the extra package named  "one-package" to the build.

::

 ./build-debian-live.sh -k 5.6.18 -g no-desktop -p "package1 package2 package3"

The example above will build a SELKS Debian 64 bit distro, no desktop with kernel ver 5.6.18
and add the extra packages named  "package1", "package2", "package3" to the build.

If you wish to do a subsequent build you need first to remove the
output directory before starting a new build: ::

 rm -rf Stamus-Live-Build/

If you plan to build SELKS multiple time you will gain time and spare bandwidth on Debian servers by using an APT proxy such as ``apt-cacher-ng``. To use it, simply set ``LB_CONFIG_OPTIONS`` variable which allow you to pass any option to ``lb config`` ::

 LB_CONFIG_OPTIONS="--apt-http-proxy http://localhost:3142/" ./build-debian-live.sh

In a similar way, you could specify a mirror: ::

 LB_CONFIG_OPTIONS="--mirror-binary http://mirror/debian/ --mirror-binary-security http://mirror/debian-security/ --mirror-binary-backports http://mirror/debian-backports/" ./build-debian-live.sh


Q&A:
1. Fix error gnupg
::
chroot chroot/
apt install gnupg2
exit

continue build: lb build 2>&1 | tee build.log