#!/usr/bin/python3

"""
    Copyright (c) 2017-2019 Ad Schellevis <ad@opnsense.org>
    All rights reserved.

    Redistribution and use in source and binary forms, with or without
    modification, are permitted provided that the following conditions are met:

    1. Redistributions of source code must retain the above copyright notice,
     this list of conditions and the following disclaimer.

    2. Redistributions in binary form must reproduce the above copyright
     notice, this list of conditions and the following disclaimer in the
     documentation and/or other materials provided with the distribution.

    THIS SOFTWARE IS PROVIDED ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES,
    INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY
    AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
    AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
    OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
    SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
    INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
    CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
    ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
    POSSIBILITY OF SUCH DAMAGE.

    --------------------------------------------------------------------------------------
    update aliases
"""

import os
import sys
import argparse
import json
import urllib3
import xml.etree.cElementTree as ET
import syslog
import subprocess
import glob
import ipaddress
from lib.alias import Alias
import lib.geoip as geoip
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def is_ipv4(s: str):
        try:
            ipaddress.IPv4Network(s)
            return True
        except ValueError:
            return False

def is_ipv6(s: str):
        try:
            ipaddress.IPv6Network(s)
            return True
        except ValueError:
            return False

class AliasParser(object):
    """ Alias Parser class, encapsulates all aliases
    """
    def __init__(self, source_tree):
        self._source_tree = source_tree
        self._aliases = dict()

    def read(self):
        """ read aliases
            :return: None
        """
        self._aliases = dict()
        alias_parameters = dict()
        alias_parameters['known_aliases'] = [x.text for x in self._source_tree.iterfind('table/name')]

        # parse general alias settings
        conf_general = self._source_tree.find('general')
        if conf_general:
            if conf_general.find('ssl_no_verify') is not None and conf_general.find('ssl_no_verify').text == "1":
                alias_parameters['ssl_no_verify'] = True

        # loop through aliases
        for elem in self._source_tree.iterfind('table'):
            alias = Alias(elem, **alias_parameters)
            self._aliases[alias.get_name()] = alias

    def get_alias_deps(self, alias, alias_deps=None):
        """ recursive fetch all alias dependencies
            :param alias: alias name
            :param alias_deps: dependencies gathered
            :return: list of aliases
        """
        if not alias_deps:
            alias_deps = list()
        if alias in self._aliases:
            for dep in self._aliases[alias].get_deps():
                if dep not in alias_deps:
                    alias_deps.append(dep)
                    self.get_alias_deps(dep, alias_deps)
        return alias_deps

    def get(self, name):
        """ get alias by name
            :param name: alias name
            :return: alias (or None if not found)
        """
        if name in self._aliases:
            return self._aliases[name]
        return None

    def __iter__(self):
        """ iterate all known aliases
            :return: iterator
        """
        for alias in self._aliases:
            yield self._aliases[alias]

if __name__ == '__main__':
    result = {'status': 'ok'}
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', help='output type [json/text]', default='json')
    parser.add_argument('--source_conf', help='configuration xml', default='/usr/local/etc/filter_tables.conf')
    inputargs = parser.parse_args()
    # make sure our target directory exists
    if not os.path.isdir('/var/db/aliastables'):
        os.makedirs('/var/db/aliastables')

    # make sure we download geoip data if not found. Since aliases only will trigger a download when change requires it
    if not os.path.isfile('/usr/local/share/GeoIP/alias.stats'):
        geoip.download_geolite()

    try:
        source_tree = ET.ElementTree(file=inputargs.source_conf)
    except ET.ParseError as e:
        syslog.syslog(syslog.LOG_ERR, 'filter table parse error (%s) %s' % (str(e), inputargs.source_conf))
        sys.exit(-1)

    aliases = AliasParser(source_tree)
    aliases.read()

    registered_aliases = set()
    for alias in aliases:
        registered_aliases.add(alias.get_name())
        # fetch alias content including dependencies
        alias_name = alias.get_name()
        alias_content = alias.resolve()
        alias_changed_or_expired = max(alias.changed(), alias.expired())
        for related_alias_name in aliases.get_alias_deps(alias_name):
            if related_alias_name != alias_name:
                rel_alias = aliases.get(related_alias_name)
                if rel_alias:
                    alias_changed_or_expired = max(alias_changed_or_expired, rel_alias.changed(), rel_alias.expired())
                    alias_content += rel_alias.resolve()
        # when the alias or any of it's dependencies has changed, generate new
        if alias_changed_or_expired:
            alias_content_txt = '\n'.join(sorted(alias_content))
            open('/var/db/aliastables/%s.txt' % alias_name, 'w').write(alias_content_txt)
        elif os.path.isfile('/var/db/aliastables/%s.txt' % alias_name):
            alias_content_txt = open('/var/db/aliastables/%s.txt' % alias_name, 'r').read()
        else:
            alias_content_txt = ""

        alias_pf_content = list()
        # nft list set ip ip_filter_table facebook | grep elements
        # ==> elements = { 192.0.2.0, 192.0.2.1 }
        sp = subprocess.run(['/usr/sbin/nft', 'list set ip ip_filter_table', alias_name, '| grep elements'], capture_output=True, text=True)
        for line in sp.stdout.strip().split('\n'):
            line = line.strip()
            if line:
                elements = map(lambda i: i.strip(), line.split('{')[1].split['}'][0].split(','))
                alias_pf_content.append(list(elements))

        if (len(alias_content) != len(alias_pf_content) or alias_changed_or_expired) and alias.get_parser():
            # if the alias is changed, expired or the one in memory has a different number of items, load table
            # (but only if we know how to handle this alias type)
            subprocess.run(['/usr/sbin/nft', 'flush set ip ip_filter_table', alias_name], capture_output=True)
            if len(alias_content) == 0:
                # flush when target is empty
                # nft flush set ip ip_filter_table facebook
                # subprocess.run(['/usr/sbin/nft', 'flush set ip ip_filter_table', alias_name], capture_output=True)
                None
            else:
                lines = open('/var/db/aliastables/%s.txt' % alias_name, 'r').read().strip().split('\n')
                elements = list(filter(is_ipv4, lines))
                # replace table contents with collected alias
                # nft add element ip ip_filter_table facebook { 192.0.2.0 }
                sp = subprocess.run(['/usr/sbin/nft', 'add element ip ip_filter_table', alias_name,
                                     '{%s}' % ','.join(elements)], capture_output=True, text=True)

                error_output = sp.stdout.strip()
                if error_output.find('nft: ') > -1:
                    result['status'] = 'error'
                    if 'messages' not in result:
                        result['messages'] = list()
                    if error_output not in result['messages']:
                        result['messages'].append(error_output.replace('nft: ', ''))

        alias_pf_content = list()
        sp = subprocess.run(['/usr/sbin/nft', 'list set ip6 ip6_filter_table', alias_name, '| grep elements'], capture_output=True, text=True)
        for line in sp.stdout.strip().split('\n'):
            line = line.strip()
            if line:
                elements = map(lambda i: i.strip(), line.split('{')[1].split['}'][0].split(','))
                alias_pf_content.append(list(elements))

        if (len(alias_content) != len(alias_pf_content) or alias_changed_or_expired) and alias.get_parser():
            # if the alias is changed, expired or the one in memory has a different number of items, load table
            # (but only if we know how to handle this alias type)
            subprocess.run(['/usr/sbin/nft', 'flush set ip6 ip6_filter_table', alias_name], capture_output=True)
            if len(alias_content) == 0:
                # flush when target is empty
                # nft flush set ip ip_filter_table facebook
                # subprocess.run(['/usr/sbin/nft', 'flush set ip ip_filter_table', alias_name], capture_output=True)
                None
            else:
                lines = open('/var/db/aliastables/%s.txt' % alias_name, 'r').read().strip().split('\n')
                elements = list(filter(is_ipv6, lines))
                # replace table contents with collected alias
                # nft add element ip ip_filter_table facebook { 192.0.2.0 }
                sp = subprocess.run(['/usr/sbin/nft', 'add element ip6 ip6_filter_table', alias_name,
                                     '{%s}' % ','.join(elements)], capture_output=True, text=True)

                error_output = sp.stdout.strip()
                if error_output.find('nft: ') > -1:
                    result['status'] = 'error'
                    if 'messages' not in result:
                        result['messages'] = list()
                    if error_output not in result['messages']:
                        result['messages'].append(error_output.replace('nft: ', ''))

    # cleanup removed aliases
    to_remove = dict()
    for filename in glob.glob('/var/db/aliastables/*.txt'):
        aliasname = os.path.basename(filename).split('.')[0]
        if aliasname not in registered_aliases:
            if aliasname not in to_remove:
                to_remove[aliasname] = list()
            to_remove[aliasname].append(filename)
    for aliasname in to_remove:
        syslog.syslog(syslog.LOG_NOTICE, 'remove old alias %s' % aliasname)
        # nft delete set ip ip_filter_table facebook
        subprocess.run(['/usr/sbin/nft', 'delete set ip ip_filter_table', aliasname], capture_output=True)
        subprocess.run(['/usr/sbin/nft', 'delete set ip6 ip6_filter_table', aliasname], capture_output=True)
        for filename in to_remove[aliasname]:
            os.remove(filename)

    print (json.dumps(result))
