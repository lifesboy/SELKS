{# Macro import #}
{% from 'OPNsense/Macros/interface.macro' import physical_interface %}
{% if not helpers.empty('Selks.SIDS.general.enabled') %}
suricata_var_script="/usr/local/opnsense/scripts/suricata/setup.sh"
suricata_enable="YES"
{% if Selks.SIDS.general.ips|default("0") == "1" %}
# IPS mode, switch to netmap
suricata_netmap="YES"
{% else %}
# SIDS mode, pcap live mode
{% set addFlags=[] %}
{%   for intfName in Selks.SIDS.general.interfaces.split(',') %}
{#     store additional interfaces to addFlags #}
{%     do addFlags.append(physical_interface(intfName)) %}
{%   endfor %}
suricata_interface="{{ addFlags|join(' ') }}"
{% endif %}
{% else %}
suricata_enable="NO"
{% endif %}
