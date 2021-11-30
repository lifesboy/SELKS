{# Macro import #}
{% from 'OPNsense/Macros/interface.macro' import physical_interface %}
{% if not helpers.empty('Selks.Anomaly.general.enabled') %}
suricata_var_script="/usr/local/opnsense/scripts/suricata/setup.sh"
suricata_enable="YES"
{% if Selks.Anomaly.general.ips|default("0") == "1" %}
# IPS mode, switch to netmap
suricata_netmap="YES"
{% else %}
# Anomaly mode, pcap live mode
{% set addFlags=[] %}
{%   for intfName in Selks.Anomaly.general.interfaces.split(',') %}
{#     store additional interfaces to addFlags #}
{%     do addFlags.append(physical_interface(intfName)) %}
{%   endfor %}
suricata_interface="{{ addFlags|join(' ') }}"
{% endif %}
{% else %}
suricata_enable="NO"
{% endif %}
