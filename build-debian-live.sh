#!/bin/bash

# Copyright Stamus Networks
# All rights reserved
# Debian Live/Install ISO script - oss@stamus-networks.com
#
# Please RUN ON Debian Buster only !!!

set -e

usage()
{
cat << EOF

usage: $0 options

########################################
#!!! RUN on Debian Buster (10) ONLY !!!#
########################################

SELKS build your own ISO options

OPTIONS:
   -h      Help info
   -g      GUI option - can be "no-desktop"
   -p      Add package(s) to the build - can be one-package or "package1 package2 package3...." (should be confined to up to 10 packages)
   -k      Kernel option - can be the stable standard version of the kernel you wish to deploy - 
           aka you can choose any kernel "3.x.x" you want.
           Example: "4.16" or "3.19.6" or "3.18.11" 
           
           More info on kernel versions and support:
           https://www.kernel.org/
           https://www.kernel.org/category/releases.html
           
   By default no options are required. The options presented here are if you wish to enable/disable/add components.
   By default SELKS will be build with a standard Debian Stretch 64 bit distro and kernel ver 4.9+ (Stretch).
   
   EXAMPLE (default): 
   ./build-debian-live.sh 
   The example above (is the default) will build a SELKS standard Debian Stretch 64 bit distro (with kernel ver 3.16)
   
   EXAMPLE (customizations): 
   
   ./build-debian-live.sh -k 4.10 
   The example above will build a SELKS Debian Stretch 64 bit distro with kernel ver 4.10
   
   ./build-debian-live.sh -k 3.18.11 -p one-package
   The example above will build a SELKS Debian Stretch 64 bit distro with kernel ver 3.18.11
   and add the extra package named  "one-package" to the build.
   
   ./build-debian-live.sh -k 3.18.11 -g no-desktop -p one-package
   The example above will build a SELKS Debian Stretch 64 bit distro, no desktop with kernel ver 3.18.11
   and add the extra package named  "one-package" to the build.
   
   ./build-debian-live.sh -k 4.16 -g no-desktop -p "package1 package2 package3"
   The example above will build a SELKS Debian Stretch 64 bit distro, no desktop with kernel ver 4.16
   and add the extra packages named  "package1", "package2", "package3" to the build.
   
   
   
EOF
}

GUI=no-desktop
KERNEL_VER=

while getopts “hg:k:p:” OPTION
do
     case $OPTION in
         h)
             usage
             exit 1
             ;;
         g)
             GUI=$OPTARG
             if [[ "$GUI" != "no-desktop" ]]; 
             then
               echo -e "\n Please check the option's spelling \n"
               usage
               exit 1;
             fi
             ;;
         k)
             KERNEL_VER=$OPTARG
             if [[ "$KERNEL_VER" =~ ^[3-5]\.[0-9]+?\.?[0-9]+$ ]];
             then
               echo -e "\n Kernel version set to ${KERNEL_VER} \n"
             else
               echo -e "\n Please check the option's spelling "
               echo -e " Also - only kernel versions >3.0 are supported !! \n"
               usage
               exit 1;
             fi
             ;;
         p)
             PKG_ADD+=("$OPTARG")
             #echo "The first value of the pkg array 'PKG_ADD' is '$PKG_ADD'"
             #echo "The whole list of values is '${PKG_ADD[@]}'"
             echo "Packages to be added to the build: ${PKG_ADD[@]} "
             #exit 1;
             ;;
         ?)
             GUI=
             KERNEL_VER=
             PKG_ADD=
             echo -e "\n Using the default options for the SELKS ISO build \n"
             ;;
     esac
done
shift $((OPTIND -1))

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 
   exit 1
fi

# Begin
# Pre staging
#

mkdir -p /binaries

if [ ! -f /binaries/libreadline8_8.1-1_amd64.deb ]; then
  wget http://ftp.de.debian.org/debian/pool/main/r/readline/libreadline8_8.1-1_amd64.deb --output-document=/binaries/libreadline8_8.1-1_amd64.deb
fi

if [ ! -f /binaries/readline-common_8.1-1_all.deb ]; then
  wget http://ftp.de.debian.org/debian/pool/main/r/readline/readline-common_8.1-1_all.deb --output-document=/binaries/readline-common_8.1-1_all.deb
fi

if [ ! -f /binaries/libparted2_3.4-1_amd64.deb ]; then
  wget http://ftp.de.debian.org/debian/pool/main/p/parted/libparted2_3.4-1_amd64.deb --output-document=/binaries/libparted2_3.4-1_amd64.deb
fi

if [ ! -f /binaries/parted_3.4-1_amd64.deb ]; then
  wget http://ftp.de.debian.org/debian/pool/main/p/parted/parted_3.4-1_amd64.deb --output-document=/binaries/parted_3.4-1_amd64.deb
fi

if [ ! -f /binaries/libfdisk1_2.36.1-8+deb11u1_amd64.deb ]; then
  wget http://ftp.de.debian.org/debian/pool/main/u/util-linux/libfdisk1_2.36.1-8+deb11u1_amd64.deb --output-document=/binaries/libfdisk1_2.36.1-8+deb11u1_amd64.deb
fi

if [ ! -f /binaries/fdisk_2.36.1-8+deb11u1_amd64.deb ]; then
  wget http://ftp.de.debian.org/debian/pool/main/u/util-linux/fdisk_2.36.1-8+deb11u1_amd64.deb --output-document=/binaries/fdisk_2.36.1-8+deb11u1_amd64.deb
fi

if [ ! -f /binaries/libext2fs2_1.46.2-2_amd64.deb ]; then
  wget http://ftp.de.debian.org/debian/pool/main/e/e2fsprogs/libext2fs2_1.46.2-2_amd64.deb --output-document=/binaries/libext2fs2_1.46.2-2_amd64.deb
fi

if [ ! -f /binaries/e2fsprogs_1.46.2-2_amd64.deb ]; then
  wget 	http://ftp.de.debian.org/debian/pool/main/e/e2fsprogs/e2fsprogs_1.46.2-2_amd64.deb --output-document=/binaries/e2fsprogs_1.46.2-2_amd64.deb
fi


if [ ! -f /binaries/cuda-repo-debian10-11-4-local_11.4.2-470.57.02-1_amd64.deb ]; then
  wget https://developer.download.nvidia.com/compute/cuda/11.4.2/local_installers/cuda-repo-debian10-11-4-local_11.4.2-470.57.02-1_amd64.deb -o /binaries/cuda-repo-debian10-11-4-local_11.4.2-470.57.02-1_amd64.deb
fi

if [ ! -f /binaries/libcudnn8_8.2.4.15-1+cuda11.4_amd64.deb ]; then
  wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/libcudnn8_8.2.4.15-1+cuda11.4_amd64.deb -o /binaries/libcudnn8_8.2.4.15-1+cuda11.4_amd64.deb
fi

if [ ! -f /binaries/libcudnn8-dev_8.2.4.15-1+cuda11.4_amd64.deb ]; then
  wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/libcudnn8-dev_8.2.4.15-1+cuda11.4_amd64.deb -o /binaries/libcudnn8-dev_8.2.4.15-1+cuda11.4_amd64.deb
fi

if [ ! -f /binaries/unetbootin-linux64-702.bin ]; then
  wget https://jaist.dl.sourceforge.net/project/unetbootin/UNetbootin/702/unetbootin-linux64-702.bin -o /binaries/unetbootin-linux64-702.bin
fi

if [ ! -d /binaries/cicflowmeter ]; then
  git clone https://github.com/lifesboy/cicflowmeter-1.git /binaries/cicflowmeter
fi

if [ ! -d /binaries/scirius ]; then
  git clone https://github.com/lifesboy/scirius.git /binaries/scirius
fi

if [ ! -d /binaries/selks ]; then
  git clone -b gpu --single-branch https://github.com/lifesboy/SELKS.git /binaries/selks
fi

if [ ! -d /binaries/suricata ]; then
  git clone -b master-6.0.x --single-branch https://github.com/lifesboy/suricata.git /binaries/suricata
  rm -rf /binaries/suricata/libhtp
  git clone -b 0.5.x --single-branch https://github.com/lifesboy/libhtp.git /binaries/suricata/libhtp
  mkdir -p /binaries/suricata/suricata-update
  cd /binaries/suricata/suricata-update
  curl -L https://github.com/OISF/suricata-update/archive/master.tar.gz | tar zxvf - --strip-components=1
  cd -
fi

if [ ! -d /binaries/squid ]; then
  git clone https://github.com/lifesboy/squid.git /binaries/squid
fi
if [ ! -d /binaries/c-icap ]; then
  #git clone -b c_icap_0_5_x --single-branch https://github.com/lifesboy/c-icap-server.git /binaries/c-icap-server
  git clone https://github.com/lifesboy/c-icap.git /binaries/c-icap
fi
if [ ! -d /binaries/c-icap-modules ]; then
  #git clone -b c_icap_0_5_x --single-branch https://github.com/lifesboy/c-icap-server.git /binaries/c-icap-server
  git clone https://github.com/lifesboy/c-icap-modules.git /binaries/c-icap-modules
fi
if [ ! -d /binaries/squidclamav ]; then
  #git clone -b v7.1 --single-branch https://github.com/lifesboy/squidclamav.git /binaries/squidclamav
  git clone https://github.com/lifesboy/squidclamav.git /binaries/squidclamav
fi
if [ ! -d /binaries/plugins ]; then
  git clone https://github.com/lifesboy/plugins.git /binaries/plugins
fi
if [ ! -d /binaries/lang ]; then
  git clone -b gpu https://github.com/lifesboy/lang.git /binaries/lang
fi

mkdir -p Stamus-Live-Build
# Hook directory for the initramfs script to be copied to
#mkdir -p config/hooks/
mkdir -p Stamus-Live-Build/config/hooks/live/

if [[ -n "$KERNEL_VER" ]]; 
then 
  
  ### START Kernel Version choice ###
  
  cd Stamus-Live-Build && mkdir -p kernel-misc && cd kernel-misc 
  if [[ ${KERNEL_VER} == 3* ]];
  then 
    wget https://www.kernel.org/pub/linux/kernel/v3.x/linux-${KERNEL_VER}.tar.xz
  elif [[ ${KERNEL_VER} == 4* ]];
  then
     wget https://www.kernel.org/pub/linux/kernel/v4.x/linux-${KERNEL_VER}.tar.xz
  elif [[ ${KERNEL_VER} == 5* ]];
  then
     wget https://www.kernel.org/pub/linux/kernel/v5.x/linux-${KERNEL_VER}.tar.xz
  else
    echo "Unsupported kernel version! Only kernel >3.0 are supported"
    exit 1;
  fi

  if [ $? -eq 0 ];
  then
    echo -e "Downloaded successfully linux-${KERNEL_VER}.tar.xz "
  else
    echo -e "\n Please check your connection \n"
    echo -e "CAN NOT download the requested kernel. Please make sure the kernel version is present here - \n"
    echo -e "https://www.kernel.org/pub/linux/kernel/v3.x/ \n"
    echo -e "or here respectively \n"
    echo -e "https://www.kernel.org/pub/linux/kernel/v4.x/ \n"
    exit 1;
  fi

  tar xfJ linux-${KERNEL_VER}.tar.xz 
  cd linux-${KERNEL_VER}
  
  # Default linux kernel config
  # Set up concurrent jobs with respect to number of CPUs
  
  make defconfig && \
  make clean && \
  make -j `getconf _NPROCESSORS_ONLN` deb-pkg LOCALVERSION=-stamus-amd64 KDEB_PKGVERSION=${KERNEL_VER}
  cd ../../
  
  # Directory where the kernel image and headers are copied to
  mkdir -p config/packages.chroot/
  # Directory that needs to be present for the Kernel Version choice to work
  mkdir -p cache/contents.chroot/
  # Hook directory for the initramfs script to be copied to
  #mkdir -p config/hooks/
  mkdir -p config/hooks/live/

  # Copy the kernel image and headers
  #mv kernel-misc/*.deb config/packages.chroot/
  #cp ../staging/config/hooks/all_chroot_update-initramfs.sh config/hooks/all_chroot_update-initramfs.chroot
  mv kernel-misc/*.deb config/packages.chroot/
  cp ../staging/config/hooks/live/all_chroot_update-initramfs.sh config/hooks/live/all_chroot_update-initramfs.chroot
    
  
  ### END Kernel Version choice ### 
  
  lb config \
  -a amd64 -d buster  \
  --archive-areas "main contrib" \
  --swap-file-size 2048 \
  --bootloader syslinux \
  --debian-installer live \
  --bootappend-live "boot=live swap config username=selks-user live-config.hostname=SELKS live-config.user-default-groups=audio,cdrom,floppy,video,dip,plugdev,scanner,bluetooth,netdev,sudo" \
  --linux-packages linux-image-${KERNEL_VER} \
  --linux-packages linux-headers-${KERNEL_VER} \
  --apt-options "--yes --force-yes" \
  --linux-flavour stamus \
  --iso-application SELKS - Suricata Elasticsearch Logstash Kibana Scirius \
  --iso-preparer Stamus Networks \
  --iso-publisher Stamus Networks \
  --iso-volume Stamus-SELKS $LB_CONFIG_OPTIONS
  
else

  cd Stamus-Live-Build && lb config \
  -a amd64 -d buster \
  --archive-areas "main contrib" \
  --swap-file-size 2048 \
  --debian-installer live \
  --bootappend-live "boot=live swap config username=selks-user live-config.hostname=SELKS live-config.user-default-groups=audio,cdrom,floppy,video,dip,plugdev,scanner,bluetooth,netdev,sudo" \
  --iso-application SELKS - Suricata Elasticsearch Logstash Kibana Scirius \
  --iso-preparer Stamus Networks \
  --iso-publisher Stamus Networks \
  --iso-volume Stamus-SELKS $LB_CONFIG_OPTIONS 

# If needed a "live" kernel can be specified like so.
# In SELKS 4 as it uses kernel >4.9 we make sure we keep the "old/unpredictable" naming convention 
# and we take care of that in chroot-inside-Debian-Live.sh
# more info - 
# https://www.freedesktop.org/wiki/Software/systemd/PredictableNetworkInterfaceNames/
#  --linux-packages linux-headers-4.9.20-stamus \
#  --linux-packages linux-image-4.9.20-stamus \
# echo "deb http://packages.stamus-networks.com/selks5/debian-kernel/ stretch main" > config/archives/stamus-kernel.list.chroot

wget -O config/archives/packages-stamus-networks-gpg.key.chroot http://packages.stamus-networks.com/packages.selks5.stamus-networks.com.gpg.key

fi

# Create dirs if not existing for the custom config files
mkdir -p config/includes.chroot/etc/logstash/conf.d/
mkdir -p config/includes.chroot/etc/skel/Desktop/
mkdir -p config/includes.chroot/usr/share/applications/
mkdir -p config/includes.chroot/usr/share/xfce4/backdrops/
mkdir -p config/includes.chroot/etc/logrotate.d/
mkdir -p config/includes.chroot/etc/systemd/system/
mkdir -p config/includes.chroot/data/moloch/etc/
mkdir -p config/includes.chroot/etc/init.d/
mkdir -p config/includes.binary/isolinux/
mkdir -p config/includes.chroot/var/log/suricata/StatsByDate/
mkdir -p config/includes.chroot/usr/share/images/desktop-base/
mkdir -p config/includes.chroot/etc/suricata/rules/
mkdir -p config/includes.chroot/etc/profile.d/
mkdir -p config/includes.chroot/root/Desktop/
mkdir -p config/includes.chroot/etc/iceweasel/profile/
mkdir -p config/includes.chroot/etc/conky/
mkdir -p config/includes.chroot/etc/alternatives/
mkdir -p config/includes.chroot/etc/systemd/system/
mkdir -p config/includes.chroot/var/backups/
mkdir -p config/includes.chroot/etc/apt/
mkdir -p config/includes.chroot/usr/share/polkit-1/actions/
mkdir -p config/includes.chroot/usr/share/polkit-1/rules.d/

cd ../

#install rst2html on debian 10
apt install docutils-common -y

# cp README and LICENSE files to the user's desktop
cp LICENSE Stamus-Live-Build/config/includes.chroot/etc/skel/Desktop/
cp LICENSE Stamus-Live-Build/config/includes.chroot/etc/skel/
# some README adjustments - in order to add a http link
# to point to the latest README version located on SELKS github
# The same as above but for root
cp LICENSE Stamus-Live-Build/config/includes.chroot/root/Desktop/
# some README adjustments - in order to add a http link
# to point to the latest README version located on SELKS github
echo -e "\nPlease make sure you have the latest README copy -> https://github.com/StamusNetworks/SELKS/tree/master \n\n" > TMP.rst
cat README.rst >> TMP.rst
cat TMP.rst | sed -e 's/https:\/\/your.selks.IP.here/http:\/\/selks/' | rst2html > Stamus-Live-Build/config/includes.chroot/etc/skel/Desktop/README.html
# same as above but for root
cat TMP.rst | sed -e 's/https:\/\/your.selks.IP.here/http:\/\/selks/' | rst2html > Stamus-Live-Build/config/includes.chroot/root/Desktop/README.html
rm TMP.rst 

# cp Scirius desktop shortcuts
cp staging/usr/share/applications/Scirius.desktop Stamus-Live-Build/config/includes.chroot/etc/skel/Desktop/
# Same as above but for root
cp staging/usr/share/applications/Scirius.desktop Stamus-Live-Build/config/includes.chroot/root/Desktop/

# Copy scirius config
cp -R staging/etc/scirius Stamus-Live-Build/config/includes.chroot/etc/

# Logstash and Elasticsearch 7 template
cp staging/etc/logstash/conf.d/logstash.conf Stamus-Live-Build/config/includes.chroot/etc/logstash/conf.d/ 
cp staging/etc/logstash/conf.d/cic.conf Stamus-Live-Build/config/includes.chroot/etc/logstash/conf.d/
cp staging/etc/logstash/conf.d/ray-result.conf Stamus-Live-Build/config/includes.chroot/etc/logstash/conf.d/
cp staging/etc/logstash/conf.d/ray-session.conf Stamus-Live-Build/config/includes.chroot/etc/logstash/conf.d/

cp staging/etc/logstash/elasticsearch7-template.json Stamus-Live-Build/config/includes.chroot/etc/logstash/
cp staging/etc/logstash/elasticsearch6-template.json Stamus-Live-Build/config/includes.chroot/etc/logstash/
cp staging/etc/logstash/elasticsearch6-cic-2017-template.json Stamus-Live-Build/config/includes.chroot/etc/logstash/
cp staging/etc/logstash/elasticsearch6-cic-2018-template.json Stamus-Live-Build/config/includes.chroot/etc/logstash/
cp staging/etc/logstash/elasticsearch6-ray-ppo-experiment-state-template.json Stamus-Live-Build/config/includes.chroot/etc/logstash/
cp staging/etc/logstash/elasticsearch6-ray-ppo-result-template.json Stamus-Live-Build/config/includes.chroot/etc/logstash/
cp staging/etc/logstash/elasticsearch6-ray-ppo-params-template.json Stamus-Live-Build/config/includes.chroot/etc/logstash/
cp staging/etc/logstash/elasticsearch6-ray-ppo-progress-template.json Stamus-Live-Build/config/includes.chroot/etc/logstash/
cp staging/etc/logstash/pipelines.yml Stamus-Live-Build/config/includes.chroot/etc/logstash/

# Moloch for SELKS set up
#cp staging/etc/systemd/system/molochpcapread-selks.service Stamus-Live-Build/config/includes.chroot/etc/systemd/system/ 
#cp staging/etc/systemd/system/molochviewer-selks.service Stamus-Live-Build/config/includes.chroot/etc/systemd/system/
#cp staging/data/moloch/etc/molochpcapread-selks-config.ini Stamus-Live-Build/config/includes.chroot/data/moloch/etc/

# Iceweasel bookmarks
cp staging/etc/iceweasel/profile/bookmarks.html Stamus-Live-Build/config/includes.chroot/etc/iceweasel/profile/

# Logrotate config for eve.json
cp staging/etc/logrotate.d/suricata Stamus-Live-Build/config/includes.chroot/etc/logrotate.d/

# Add the Stmaus Networs logo for the boot screen
cp staging/splash.png Stamus-Live-Build/config/includes.binary/isolinux/

# Add the SELKS wallpaper
cp staging/wallpaper/joy-wallpaper_1920x1080.svg Stamus-Live-Build/config/includes.chroot/etc/alternatives/desktop-background
#cp staging/wallpaper/joy-wallpaper_1920x1080.svg Stamus-Live-Build/config/includes.chroot/usr/share/xfce4/backdrops/

# Copy banners
cp staging/etc/motd Stamus-Live-Build/config/includes.chroot/etc/
cp staging/etc/issue.net Stamus-Live-Build/config/includes.chroot/etc/

# Copy pythonpath.sh
cp staging/etc/profile.d/pythonpath.sh Stamus-Live-Build/config/includes.chroot/etc/profile.d/

# Copy evebox desktop shortcut.
cp staging/usr/share/applications/Evebox.desktop Stamus-Live-Build/config/includes.chroot/etc/skel/Desktop/

# Same as above but for root
cp staging/usr/share/applications/Evebox.desktop Stamus-Live-Build/config/includes.chroot/root/Desktop/

# Copy set up IDS interface desktop shortcut.
cp staging/usr/share/applications/Setup-IDS-Interface.desktop Stamus-Live-Build/config/includes.chroot/etc/skel/Desktop/
chmod +x Stamus-Live-Build/config/includes.chroot/etc/skel/Desktop/Setup-IDS-Interface.desktop

# Same as above but for root
#cp staging/usr/share/applications/Setup-IDS-Interface.desktop Stamus-Live-Build/config/includes.chroot/root/Desktop/

# Copy first time set up desktop shortcut.
cp staging/usr/share/applications/FirstTime-Setup.desktop Stamus-Live-Build/config/includes.chroot/etc/skel/Desktop/
chmod +x Stamus-Live-Build/config/includes.chroot/etc/skel/Desktop/FirstTime-Setup.desktop

# Same as above but for root
#cp staging/usr/share/applications/FirstTime-Setup.desktop Stamus-Live-Build/config/includes.chroot/root/Desktop/

# Copy upgrade SELKS desktop shortcut.
cp staging/usr/share/applications/Upgrade-SELKS.desktop Stamus-Live-Build/config/includes.chroot/etc/skel/Desktop/
chmod +x Stamus-Live-Build/config/includes.chroot/etc/skel/Desktop/Upgrade-SELKS.desktop

# Same as above but for root
#cp staging/usr/share/applications/Upgrade-SELKS.desktop Stamus-Live-Build/config/includes.chroot/root/Desktop/

# copy polkit policies for selks-user to be able to execute as root 
# first time setup scripts
cp staging/usr/share/polkit-1/actions/org.stamusnetworks.firsttimesetup.policy Stamus-Live-Build/config/includes.chroot/usr/share/polkit-1/actions/
cp staging/usr/share/polkit-1/actions/org.stamusnetworks.setupidsinterface.policy Stamus-Live-Build/config/includes.chroot/usr/share/polkit-1/actions/
cp staging/usr/share/polkit-1/actions/org.stamusnetworks.update.policy Stamus-Live-Build/config/includes.chroot/usr/share/polkit-1/actions/
cp staging/usr/share/polkit-1/rules.d/org.stamusnetworks.rules Stamus-Live-Build/config/includes.chroot/usr/share/polkit-1/rules.d/

# copy opnsense source
mkdir -p Stamus-Live-Build/chroot/usr/local
mkdir -p Stamus-Live-Build/chroot/usr/local/etc
mkdir -p Stamus-Live-Build/chroot/usr/share
mkdir -p Stamus-Live-Build/chroot/usr/lib/php/20180731/build
mkdir -p Stamus-Live-Build/conf
mkdir -p Stamus-Live-Build/chroot/etc/php/7.3/cli

cp -R staging/usr/local/opnsense Stamus-Live-Build/chroot/usr/local
cp -R staging/usr/local/wizard Stamus-Live-Build/chroot/usr/local
cp -R staging/usr/local/www Stamus-Live-Build/chroot/usr/local
cp -R staging/usr/local/etc/inc Stamus-Live-Build/chroot/usr/local/etc/
cp -R staging/usr/local/etc/ssl Stamus-Live-Build/chroot/usr/local/etc/
cp -R staging/usr/local/etc/config.xml Stamus-Live-Build/chroot/usr/local/etc/
cp -R staging/conf Stamus-Live-Build/chroot/

cp -R staging/usr/share/google-api-php-client Stamus-Live-Build/chroot/usr/share
cp -f staging/etc/php/7.3/cli/php.ini Stamus-Live-Build/chroot/etc/php/7.3/cli/php.ini
#cp -R staging/etc/php/7.3/cli/conf.d /etc/php/7.3/cli/

#cp -R staging/usr/lib/php /usr/lib/
rm -f /usr/lib/php/20180731/phalcon.so
cp -f staging/usr/lib/php/20180731/phalcon.so Stamus-Live-Build/chroot/usr/lib/php/20180731/

cp -R staging/etc/lighttpd Stamus-Live-Build/chroot/etc/

chown -R www-data:www-data Stamus-Live-Build/chroot/conf Stamus-Live-Build/chroot/usr/local/etc

# cp OPNSense desktop shortcuts
cp staging/usr/share/applications/NGFW.desktop Stamus-Live-Build/config/includes.chroot/etc/skel/Desktop/

# copy nvidia binaries
mkdir -p Stamus-Live-Build/chroot/binaries/

cp /binaries/libreadline8_8.1-1_amd64.deb Stamus-Live-Build/chroot/binaries/
cp /binaries/readline-common_8.1-1_all.deb Stamus-Live-Build/chroot/binaries/
cp /binaries/libparted2_3.4-1_amd64.deb Stamus-Live-Build/chroot/binaries/
cp /binaries/parted_3.4-1_amd64.deb Stamus-Live-Build/chroot/binaries/
cp /binaries/libfdisk1_2.36.1-8+deb11u1_amd64.deb Stamus-Live-Build/chroot/binaries/
cp /binaries/fdisk_2.36.1-8+deb11u1_amd64.deb Stamus-Live-Build/chroot/binaries/
cp /binaries/libext2fs2_1.46.2-2_amd64.deb Stamus-Live-Build/chroot/binaries/
cp /binaries/e2fsprogs_1.46.2-2_amd64.deb Stamus-Live-Build/chroot/binaries/

cp /binaries/cuda-repo-debian10-11-4-local_11.4.2-470.57.02-1_amd64.deb Stamus-Live-Build/chroot/binaries/
cp /binaries/libcudnn8_8.2.4.15-1+cuda11.4_amd64.deb Stamus-Live-Build/chroot/binaries/
cp /binaries/libcudnn8-dev_8.2.4.15-1+cuda11.4_amd64.deb Stamus-Live-Build/chroot/binaries/
cp /binaries/unetbootin-linux64-702.bin Stamus-Live-Build/chroot/binaries/
cp -R /binaries/cicflowmeter Stamus-Live-Build/chroot/binaries/
cp -R /binaries/scirius Stamus-Live-Build/chroot/binaries/
cp -R /binaries/selks Stamus-Live-Build/chroot/binaries/
cp -R /binaries/suricata Stamus-Live-Build/chroot/binaries/
cp -R /binaries/squid Stamus-Live-Build/chroot/binaries/
cp -R /binaries/c-icap Stamus-Live-Build/chroot/binaries/
cp -R /binaries/c-icap-modules Stamus-Live-Build/chroot/binaries/
cp -R /binaries/squidclamav Stamus-Live-Build/chroot/binaries/
cp -R /binaries/plugins Stamus-Live-Build/chroot/binaries/
cp -R /binaries/lang Stamus-Live-Build/chroot/binaries/

# Add core system packages to be installed
echo "

libpcre3 libpcre3-dbg libpcre3-dev ntp
build-essential autoconf automake libtool libpcap-dev libnet1-dev 
libyaml-0-2 libyaml-dev zlib1g zlib1g-dev libcap-ng-dev libcap-ng0 
make flex bison git git-core libmagic-dev libnuma-dev pkg-config
libnetfilter-queue-dev libnetfilter-queue1 libnfnetlink-dev libnfnetlink0 
libjansson-dev libjansson4 libnss3-dev libnspr4-dev libgeoip1 libgeoip-dev 
rsync mc python-daemon libnss3-tools curl net-tools
python-crypto libgmp10 libyaml-0-2 python-simplejson python-pygments
python-yaml ssh sudo tcpdump nginx openssl jq patch  
python-pip debian-installer-launcher live-build apt-transport-https
gnupg2
 " \
>> Stamus-Live-Build/config/package-lists/StamusNetworks-CoreSystem.list.chroot

# Add system tools packages to be installed
echo "
ethtool bwm-ng iptraf htop rsync tcpreplay sysstat hping3 screen ngrep 
tcpflow dsniff mc python-daemon wget curl vim bootlogd lsof libpolkit-agent-1-0 libpolkit-backend-1-0 libpolkit-gobject-1-0 policykit-1 policykit-1-gnome" \
>> Stamus-Live-Build/config/package-lists/StamusNetworks-Tools.list.chroot

# Unless otherwise specified the ISO will be with a Desktop Environment
if [[ -z "$GUI" ]]; then 
  #echo "lxde fonts-lyx wireshark terminator conky" \
  #>> Stamus-Live-Build/config/package-lists/StamusNetworks-Gui.list.chroot
  echo "task-xfce-desktop xfce4-goodies fonts-lyx wireshark terminator" \
  >> Stamus-Live-Build/config/package-lists/StamusNetworks-Gui.list.chroot
  echo "wireshark terminator open-vm-tools open-vm-tools lxpolkit" \
  >> Stamus-Live-Build/config/package-lists/StamusNetworks-Gui.list.chroot
  
  #echo "task-xfce-desktop" >> Stamus-Live-Build/config/package-lists/desktop.list.chroot
  # Copy conky conf file
  cp staging/etc/conky/conky.conf Stamus-Live-Build/config/includes.chroot/etc/conky/
  # Copy the menu shortcuts for Kibana and Scirius
  # this is for the lxde menu widgets - not the desktop shortcuts
  cp staging/usr/share/applications/Scirius.desktop Stamus-Live-Build/config/includes.chroot/usr/share/applications/

  # For Evebox to.
  cp staging/usr/share/applications/Evebox.desktop Stamus-Live-Build/config/includes.chroot/usr/share/applications/
  
  # For setting up Suricata IDS interface.
  cp staging/usr/share/applications/Setup-IDS-Interface.desktop Stamus-Live-Build/config/includes.chroot/usr/share/applications/
  
  # First time setup/init.
  cp staging/usr/share/applications/FirstTime-Setup.desktop Stamus-Live-Build/config/includes.chroot/usr/share/applications/
fi

# If -p (add packages) option is used - add those packages to the build
if [[ -n "${PKG_ADD}" ]]; then 
  echo " ${PKG_ADD[@]} " >> \
  Stamus-Live-Build/config/package-lists/StamusNetworks-UsrPkgAdd.list.chroot
fi

# Add specific tasks(script file) to be executed 
# inside the chroot environment
cp staging/config/hooks/live/chroot-inside-Debian-Live.hook.chroot Stamus-Live-Build/config/hooks/live/
cp staging/config/hooks/live/moreutil.hook.chroot Stamus-Live-Build/config/hooks/live/

# Edit menu names for Live and Install
if [[ -n "$KERNEL_VER" ]]; 
then
  
   # IF custom kernel option is chosen "-k ...":
   # remove the live menu since different kernel versions and custom flavors  
   # can potentially fail to load in LIVE depending on the given environment.
   # So we create a file for execution at the binary stage to remove the 
   # live menu choice. That leaves the options to install.
   cp staging/config/hooks/live/menues-changes.hook.binary Stamus-Live-Build/config/hooks/live/
   cp staging/config/hooks/live/menues-changes-live-custom-kernel-choice.hook.binary Stamus-Live-Build/config/hooks/live/
   
   
else
  
  #cp staging/config/hooks/menues-changes.binary Stamus-Live-Build/config/hooks/
  cp staging/config/hooks/live/menues-changes.hook.binary Stamus-Live-Build/config/hooks/live/
  
fi

# Debian installer preseed.cfg
echo "
d-i netcfg/hostname string SELKS

d-i passwd/user-fullname string selks-user User
d-i passwd/username string selks-user
d-i passwd/user-password password selks-user
d-i passwd/user-password-again password selks-user
d-i passwd/user-default-groups string audio cdrom floppy video dip plugdev scanner bluetooth netdev sudo

d-i passwd/root-password password StamusNetworks
d-i passwd/root-password-again password StamusNetworks
" > Stamus-Live-Build/config/includes.installer/preseed.cfg

# should stop current running db to avoid conflict for later steps
pg_ctlcluster 11 main stop || true
killall -9 postgres || true

# Build the ISO
cd Stamus-Live-Build && ( lb build 2>&1 | tee build.log )
#cd Stamus-Live-Build && ( lb build &> build.log )
#mv binary.hybrid.iso SELKS.iso
mv live-image-amd64.hybrid.iso SELKS.iso
