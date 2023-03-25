<?php

/*
 * Copyright (C) 2017 Deciso B.V.
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *
 * 1. Redistributions of source code must retain the above copyright notice,
 *    this list of conditions and the following disclaimer.
 *
 * 2. Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the distribution.
 *
 * THIS SOFTWARE IS PROVIDED ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES,
 * INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY
 * AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
 * AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
 * OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 * SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 * INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
 * CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 * POSSIBILITY OF SUCH DAMAGE.
 */

namespace OPNsense\Firewall;

/**
 * Class Rule basic rule parsing logic
 * @package OPNsense\Firewall
 */
abstract class Rule
{
    protected $rule = array();
    protected $interfaceMapping = array();
    protected $ruleDebugInfo = array();

    /**
     * init Rule
     * @param array $interfaceMapping internal interface mapping
     * @param array $conf rule configuration
     */
    public function __construct(&$interfaceMapping, $conf)
    {
        $this->interfaceMapping = $interfaceMapping;
        $this->rule = $conf;
    }

    /**
     * send text to debug log
     * @param string debug log info
     */
    protected function log($line)
    {
        $this->ruleDebugInfo[] = $line;
    }

    /**
     * output parsing
     * @param string $value field value
     * @return string
     */
    protected function parseIsComment($value)
    {
        return !empty($value) ? "# add rule" : "add rule";
    }

    /**
     * parse comment
     * @param string $value field value
     * @return string
     */
    protected function parseComment($value)
    {
        return !empty($value) ? "# " . preg_replace("/\r|\n/", "", $value) : "";
    }

    /**
     * parse static text
     * @param string $value static text
     * @param string $text
     * @return string
     */
    protected function parseStaticText($value, $text)
    {
        return $text;
    }

    /**
     * parse boolean, return text from $valueTrue / $valueFalse
     * @param string $value field value
     * @param $valueTrue
     * @param string $valueFalse
     * @return string
     */
    protected function parseBool($value, $valueTrue, $valueFalse = "")
    {
        if (!empty($value) && boolval($value)) {
            return !empty($valueTrue) ? $valueTrue . " " : "";
        } else {
            return !empty($valueFalse) ? $valueFalse . " " : "";
        }
    }

    /**
     * parse plain data
     * @param string $value field value
     * @param string $prefix prefix when $value is provided
     * @param string $suffix suffix when $value is provided
     * @param int $maxsize maximum size, cut when longer
     * @return string
     */
    protected function parsePlain($value, $prefix = "", $suffix = "", $maxsize = null)
    {
        if (!empty($maxsize) && strlen($value) > $maxsize) {
            $value = substr($value, 0, $maxsize);
        }
        return $value == null || $value === '' ? '' : $prefix . $value . $suffix . ' ';
    }

    /**
     * parse plain data
     * @param string $value field value
     * @param string $prefix prefix when $value is provided
     * @param string $suffix suffix when $value is provided
     * @return string
     */
    protected function parsePlainCurly($value, $prefix = "", $suffix = "")
    {
        if (strpos($value, '$') === false && strpos($value, '@') === false) {
            // don't wrap aliases in curly brackets
            $prefix = $prefix . "{";
            $suffix = "}" . $suffix;
        }
        return $value == null || $value === '' ? '' : $prefix . $value . $suffix . ' ';
    }

    /**
     * parse data, use replace map
     * @param string $value field value
     * @param string $map
     * @return string
     */
    protected function parseReplaceSimple($value, $map, $prefix = "", $suffix = "")
    {
        $retval = $value;
        foreach (explode('|', $map) as $item) {
            $tmp = explode(':', $item);
            if ($tmp[0] == $value) {
                $retval = $tmp[1];
                break;
            }
        }
        if (!empty($retval)) {
            return $prefix . $retval . $suffix . " ";
        } else {
            return "";
        }
    }

    protected function parseReplaceSimpleAllowZero($value, $map, $prefix = "", $suffix = "")
    {
        $retval = $value;
        foreach (explode('|', $map) as $item) {
            $tmp = explode(':', $item);
            if ($tmp[0] === $value) {
                $retval = $tmp[1];
                break;
            }
        }
        if ($retval !== '') {
            return $prefix . $retval . $suffix . " ";
        } else {
            return "";
        }
    }

    /**
     * parse data, use replace map
     * @param string $value field value
     * @param string $map
     * @return string
     */
    protected function parseReplaceVariable($value, $map, $prefix = "", $suffix = "")
    {
        $retval = $value;
        foreach (explode('|', $map) as $item) {
            $tmp = explode(':', $item);
            if ($tmp[0] == $value) {
                $retval = $tmp[1];
                break;
            }
        }
        if (!empty($retval)) {
            $mapval = $retval;
            $retval = $prefix . $retval . $suffix;
            $retval = str_replace('{value}', $value, $retval);
            $retval = str_replace('{map}', $mapval, $retval);
            return $retval . " ";
        } else {
            return "";
        }
    }

    /**
     * rule reader, applies standard rule patterns
     * @param string type of rule to be read
     * @return iterator rules to generate
     */
    protected function reader($type = null)
    {
        $interfaces = empty($this->rule['interface']) ? array(null) : explode(',', $this->rule['interface']);
        foreach ($interfaces as $interface) {
            if (isset($this->rule['ipprotocol']) && $this->rule['ipprotocol'] == 'inet46') {
                $ipprotos = array('inet', 'inet6');
            } elseif (isset($this->rule['ipprotocol'])) {
                $ipprotos = array($this->rule['ipprotocol']);
            } elseif (!empty($type) && $type = 'npt') {
                $ipprotos = array('inet6');
            } else {
                $ipprotos = array(null);
            }

            foreach ($ipprotos as $ipproto) {
                if (isset($this->rule['protocol']) && $this->rule['protocol'] == 'tcp/udp') {
                    $protos = array('tcp', 'udp');
                } else if (isset($this->rule['protocol'])) {
                    $protos = array($this->rule['protocol']);
                } else {
                    $protos = array(null);
                }

                foreach ($protos as $proto) {
                    $rule = $this->rule;
                    if ($ipproto == 'inet6' && !empty($this->interfaceMapping[$interface]['IPv6_override'])) {
                        $rule['interface'] = $this->interfaceMapping[$interface]['IPv6_override'];
                    } else {
                        $rule['interface'] = $interface;
                    }
                    $rule['ipprotocol'] = $ipproto;
                    $rule['protocol'] = $proto;
                    $this->convertAddress($rule);
                    // disable rule when interface not found
                    if (!empty($interface) && empty($this->interfaceMapping[$interface]['if'])) {
                        $this->log("Interface {$interface} not found");
                        $rule['disabled'] = true;
                    }
                    yield $rule;
                }
            }
        }
    }

    /**
     * parse rule to text using processing parameters in $procorder
     * @param array conversion properties (rule keys and methods to execute)
     * @param array rule to parse
     * @return string
     */
    protected function ruleToText(&$procorder, &$rule)
    {
        $ruleTxt = '';
        foreach ($procorder as $tag => $handle) {
            // support reuse of the same fieldname
            // $tag = explode(".", $tag)[0];
            $tags = explode(',', $tag);
            $tmp = explode(',', $handle);
            $method = $tmp[0];
            // $args = array(isset($rule[$tag]) ? $rule[$tag] : null);
            $args = array_map(function ($i) use (&$rule) {
                $t = explode(".", $i)[0];
                return isset($rule[$t]) ? $rule[$t] : null;
            }, $tags);
            if (count($tmp) > 1) {
                array_shift($tmp);
                $args = array_merge($args, $tmp);
            }
            $cmdout = trim(call_user_func_array(array($this,$method), $args));
            $ruleTxt .= !empty($cmdout) && !empty($ruleTxt) ? " "  : "";
            $ruleTxt .= $cmdout;
        }
        if (!empty($this->ruleDebugInfo)) {
            $debugTxt = "#debug:" . implode("|", $this->ruleDebugInfo) . "\n";
        } else {
            $debugTxt = "";
        }
        return $debugTxt . $ruleTxt;
    }

    /**
     * convert source/destination address entries as used by the gui
     * @param array $rule rule
     */
    protected function convertAddress(&$rule)
    {
        $fields = array();
        $fields['source'] = 'from';
        $fields['destination'] = 'to';
        $interfaces = $this->interfaceMapping;
        foreach ($fields as $tag => $target) {
            if (!empty($rule[$tag])) {
                if (isset($rule[$tag]['any'])) {
                    $rule[$target] = 'any';
                } elseif (!empty($rule[$tag]['network'])) {
                    $network_name = $rule[$tag]['network'];
                    $matches = "";
                    if (trim($network_name) == 'this_firewall' || trim($network_name) == '(self)') {
                        $rule[$target] = '$this_firewall' . $this->parseReplaceSimple($rule['ipprotocol'], 'inet:ip|inet6:ip6', '_');
                    } elseif (preg_match("/^(wan|lan|opt[0-9]+)ip$/", $network_name, $matches)) {
                        if (!empty($interfaces[$matches[1]]['if'])) {
                            // $rule[$target] = "({$interfaces["{$matches[1]}"]['if']})";
                            $rule[$target] = '$' . $matches[1] . "_address" . $this->parseReplaceSimple($rule['ipprotocol'], 'inet:ip|inet6:ip6', '_');;
                        }
                    } elseif (!empty($interfaces[$network_name]['if'])) {
                        // $rule[$target] = "({$interfaces[$network_name]['if']}:network)";
                        $rule[$target] = '$' . $network_name . "_net" . $this->parseReplaceSimple($rule['ipprotocol'], 'inet:ip|inet6:ip6', '_');;
                    } elseif (Util::isIpAddress($rule[$tag]['network']) || Util::isSubnet($rule[$tag]['network'])) {
                        $rule[$target] = $rule[$tag]['network'];
                    } elseif (Util::isAlias($rule[$tag]['network'])) {
                        $rule[$target] = '@' . $rule[$tag]['network'];
                    } elseif ($rule[$tag]['network'] == 'any') {
                        $rule[$target] = $rule[$tag]['network'];
                    }
                } elseif (!empty($rule[$tag]['address'])) {
                    if (
                        Util::isIpAddress($rule[$tag]['address']) || Util::isSubnet($rule[$tag]['address']) ||
                        Util::isPort($rule[$tag]['address'])
                    ) {
                        $rule[$target] = $rule[$tag]['address'];
                    } elseif (Util::isAlias($rule[$tag]['address'])) {
                        $rule[$target] = '@' . $rule[$tag]['address'];
                    }
                }
                if (!empty($rule[$target]) && $rule[$target] != 'any' && isset($rule[$tag]['not'])) {
                    $rule[$target] = "!= " . $rule[$target];
                }
                if (isset($rule['protocol']) && in_array(strtolower($rule['protocol']), array("tcp","udp","tcp/udp"))) {
                    $port = str_replace('-', ':', $rule[$tag]['port']);
                    if (Util::isPort($port)) {
                        $rule[$target . "_port"] = $port;
                    } elseif (Util::isAlias($port)) {
                        $rule[$target . "_port"] = '@' . $port;
                        if (!Util::isAlias($port, true)) {
                            // unable to map port
                            $rule['disabled'] = true;
                            $this->log("Unable to map port {$port}, empty?");
                        }
                    }
                }
                if (!isset($rule[$target])) {
                    // couldn't convert address, disable rule
                    // dump all tag contents in target (from/to) for reference
                    $rule['disabled'] = true;
                    $this->log("Unable to convert address, see {$target} for details");
                    $rule[$target] = json_encode($rule[$tag]);
                }
            }
        }
    }

    /**
     * parse interface (name to interface)
     * @param string|array $value field value
     * @param string $prefix prefix interface tag
     * @return string
     */
    protected function parseInterface($value, $prefix = "iif ", $suffix = "")
    {
        if (empty($value)) {
            return "";
        } elseif (empty($this->interfaceMapping[$value]['if'])) {
            return "{$prefix}\${$value}{$suffix} ";
        } else {
            return "{$prefix}" . $this->interfaceMapping[$value]['if'] . "{$suffix} ";
        }
    }

    protected function parseAdvanceProtocol($ipprotocol, $protocol, $to_port, $prefix = "", $suffix = "")
    {
        $ipprotocol = $this->parseReplaceSimple($ipprotocol, 'inet:ip protocol|inet4:ip protocol|inet6:ip6 nexthdr|:ip protocol|ip:ip protocol|ip6:ip6 nexthdr');
        $protocol = empty($to_port)
            ? trim($this->parseReplaceSimple($protocol, 'inet:|inet4:|inet6:|ip:|ip6:|tcp/udp:|ipv6-icmp:|icmpv6:'))
            : trim($this->parseReplaceSimple($protocol, 'inet:|inet4:|inet6:|ip:|ip6:|tcp:|udp:|tcp/udp:|ipv6-icmp:|icmpv6:'));
        if (!empty($protocol) && strpos($protocol, '$') === false && strpos($protocol, '@') === false) {
            // don't wrap aliases in curly brackets
            $protocol = "{" . $protocol . "}";
        }
        $value = empty($protocol) ? '' : $ipprotocol . $protocol;
        return empty($value) ? '' : $prefix . $value . $suffix . ' ';
    }

    protected function parseLog($log, $logPrefix, $prefix = "", $suffix = "")
    {
        $value = $this->parsePlain(empty($logPrefix) ? 'nft log_' : $logPrefix, 'log prefix "', '"');
        return $this->parseBool($log, $prefix . $value . $suffix . ' ', '');
    }

    protected function parseFrom($ipprotocol, $protocol, $from, $from_port, $prefix = "", $suffix = "")
    {
        $ipprotocol = $this->parseReplaceSimple($ipprotocol, 'inet:ip|inet4:ip|inet6:ip6|:ip');
        $from = trim($this->parseReplaceSimple($from, 'any:'));
        if (!empty($from) && strpos($from, '$') === false && strpos($from, '@') === false) {
            // don't wrap aliases in curly brackets
            $pure_from = explode('!=', $from);
            $from = empty($pure_from[0]) && !empty($pure_from[1]) ? "!={" . $pure_from[1] . "}" : "{" . $from . "}";
        }
        $from_port = trim($this->parseReplaceSimpleAllowZero($from_port, 'any:'));
        $from_port = str_replace(':', '-', $from_port);
        if ($from_port != '' && strpos($from_port, '$') === false && strpos($from_port, '@') === false) {
            // don't wrap aliases in curly brackets
            $from_port = "{" . implode(',', explode(' ', $from_port)) . "}";
        }
        $value = empty($from) ? '' : $ipprotocol . 'saddr ' . $from;
        $value .= $from_port == '' ? ''
            : $this->parseReplaceSimple($protocol, 'any:|tcp/udp:', ' ') . ' sport ' . $from_port;
        return empty($value) ? '' : $prefix . $value . $suffix . ' ';
    }

    protected function parseTo($ipprotocol, $protocol, $to, $to_port, $prefix = "", $suffix = "")
    {
        $ipprotocol = $this->parseReplaceSimple($ipprotocol, 'inet:ip|inet4:ip|inet6:ip6|:ip');
        $to = trim($this->parseReplaceSimple($to, 'any:'));
        if (!empty($to) && strpos($to, '$') === false && strpos($to, '@') === false) {
            // don't wrap aliases in curly brackets
            $pure_to = explode('!=', $to);
            $to = empty($pure_to[0]) && !empty($pure_to[1]) ? "!={" . $pure_to[1] . "}" : "{" . $to . "}";
        }
        $to_port = trim($this->parseReplaceSimpleAllowZero($to_port, 'any:'));
        $to_port = str_replace(':', '-', $to_port);
        if ($to_port != '' && strpos($to_port, '$') === false && strpos($to_port, '@') === false) {
            // don't wrap aliases in curly brackets
            $to_port = "{" . implode(',', explode(' ', $to_port)) . "}";
        }
        $value = empty($to) ? '' : $ipprotocol . 'daddr ' . $to;
        $value .= $to_port  == '' ? '' :
            $this->parseReplaceSimple($protocol, 'any:|tcp/udp:', ' ') . ' dport ' . $to_port;
        return empty($value) ? '' : $prefix . $value . $suffix . ' ';
    }

    /**
     * Validate if the provided rule looks like an ipv4 address.
     * This method isn't bulletproof (if only aliases are used and we don't know the protocol, this might fail to
     * tell the truth)
     * @param array $rule parsed rule info
     * @return bool
     */
    protected function isIpV4($rule)
    {
        if (!empty($rule['ipprotocol'])) {
            return $rule['ipprotocol'] == 'inet';
        } else {
            // check fields which are known to contain addresses and search for an ipv4 address
            foreach (array('from', 'to', 'external', 'target') as $fieldname) {
                if (
                    (Util::isIpAddress($rule[$fieldname]) || Util::isSubnet($rule[$fieldname]))
                        && strpos($rule[$fieldname], ":") === false
                ) {
                    return true;
                }
            }
            return false;
        }
    }

    /**
     * return label
     * @return string
     */
    public function getLabel()
    {
        return !empty($this->rule['label']) ? $this->rule['label'] : "";
    }

    /**
     * return #ref
     * @return string
     */
    public function getRef()
    {
        return !empty($this->rule['#ref']) ? $this->rule['#ref'] : "";
    }

    /**
     * return description
     * @return string
     */
    public function getDescr()
    {
        return !empty($this->rule['descr']) ? $this->rule['descr'] : "";
    }

    /**
     * return interface
     */
    public function getInterface()
    {
        return !empty($this->rule['interface']) ? $this->rule['interface'] : "";
    }

    /**
     * is rule enabled
     */
    public function isEnabled()
    {
        return empty($this->rule['disabled']);
    }

    /**
     * return raw rule
     */
    public function getRawRule()
    {
        return $this->rule;
    }
}
