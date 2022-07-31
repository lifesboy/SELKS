<?php

/*
 * Copyright (C) 2015-2017 Deciso B.V.
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

namespace Selks\Anomaly\Api;

use Phalcon\Filter;
use OPNsense\Base\ApiMutableModelControllerBase;
use OPNsense\Base\Filters\QueryFilter;
use OPNsense\Core\Backend;
use OPNsense\Core\Config;
use OPNsense\Base\UIModelGrid;

/**
 * Class DataProcessorSettingsController Handles settings related API actions for the Anomaly module
 * @package Selks\Anomaly
 */
class TestingSettingsController extends ApiMutableModelControllerBase
{
    protected static $internalModelName = 'anomaly';
    protected static $internalModelClass = '\Selks\Anomaly\Anomaly';

    /**
     * Query non layered model items
     * @return array plain model settings (non repeating items)
     * @throws \ReflectionException when not bound to model
     */
    protected function getModelNodes()
    {
        $settingsNodes = array('testing');
        $result = array();
        $mdlAnomaly = $this->getModel();
        foreach ($settingsNodes as $key) {
            $result[$key] = $mdlAnomaly->$key->getNodes();
        }
        return $result;
    }

    /**
     * Search installed anomaly rules
     * @return array query results
     * @throws \Exception when configd action fails
     * @throws \ReflectionException when not bound to model
     */
    public function searchLocalDatasetsAction()
    {
        if ($this->request->isPost()) {
            $this->sessionClose();
            // create filter to sanitize input data
            $filter = new Filter();
            $filter->add('query', new QueryFilter());


            // fetch query parameters (limit results to prevent out of memory issues)
            $itemsPerPage = $this->request->getPost('rowCount', 'int', 9999);
            $currentPage = $this->request->getPost('current', 'int', 1);

            if ($this->request->hasPost('sort') && is_array($this->request->getPost("sort"))) {
                $sortStr = '';
                $sortBy = array_keys($this->request->getPost("sort"));
                if ($this->request->getPost("sort")[$sortBy[0]] == "desc") {
                    $sortOrd = 'desc';
                } else {
                    $sortOrd = 'asc';
                }

                foreach ($sortBy as $sortKey) {
                    if ($sortStr != '') {
                        $sortStr .= ',';
                    }
                    $sortStr .= $filter->sanitize($sortKey, "query") . ' ' . $sortOrd . ' ';
                }
            } else {
                $sortStr = 'sid';
            }
            if ($this->request->getPost('searchPhrase', 'string', '') != "") {
                $searchTag = $filter->sanitize($this->request->getPost('searchPhrase'), "query");
                $searchPhrase = 'msg,source,sid,artifact/"' . $searchTag . '"';
            } else {
                $searchPhrase = '';
            }

            // add metadata filters
            foreach ($_POST as $key => $value) {
                $key = $filter->sanitize($key, "string");
                $value = $filter->sanitize($value, "string");
                if (!in_array($key, ['current', 'rowCount', 'sort', 'searchPhrase', 'action'])) {
                    $searchPhrase .= " {$key}/{$value} ";
                }
            }

            // add filter for action
            if ($this->request->getPost("action", "string", '') != "") {
                $searchTag = $filter->sanitize($this->request->getPost('action'), "query");
                $searchPhrase .= " installed_action/" . $searchTag . ' ';
            }

            // request list of installed rules
            $backend = new Backend();
            $response = $backend->configdpRun("anomaly query datasets", array($itemsPerPage,
                ($currentPage - 1) * $itemsPerPage,
                $searchPhrase, $sortStr));

            $data = json_decode($response, true);

            if ($data != null && array_key_exists("rows", $data)) {
                $result = array();
                $result['rows'] = $data['rows'];
                // update rule status with own administration
                foreach ($result['rows'] as &$row) {
                    $row['enabled_default'] = $row['enabled'];
                    $row['enabled'] = $this->getModel()->getTestingDatasetStatus($row['sid'], $row['enabled']);
                    $row['action'] = $this->getModel()->getTestingDatasetAction($row['sid'], $row['action'], true);
                }

                $result['rowCount'] = empty($result['rows']) || !is_array($result['rows']) ? 0 : count($result['rows']);
                $result['total'] = $data['total_rows'];
                $result['parameters'] = $data['parameters'];
                $result['current'] = (int)$currentPage;
                return $result;
            } else {
                return array('error' => array('msg' => 'timeout'));
            }
        } else {
            return array('error' => array('msg' => 'invalid format'));
        }
    }

    /**
     * Get rule information
     * @param string|null $sid rule identifier
     * @return array|mixed
     * @throws \Exception when configd action fails
     * @throws \ReflectionException when not bound to model
     */
    public function getDatasetInfoAction($sid = null)
    {
        // request list of installed rules
        if (!empty($sid)) {
            $this->sessionClose();
            $backend = new Backend();
            $response = $backend->configdpRun("anomaly query datasets", array(1, 0,'sid/' . $sid));
            $data = json_decode($response, true);
        } else {
            $data = null;
        }

        if ($data != null && array_key_exists("rows", $data) && !empty($data['rows'])) {
            $row = $data['rows'][0];
            // set current enable status (default + registered offset)
            $row['enabled_default'] = $row['enabled'];
            $row['action_default'] = $row['action'];
            $row['enabled'] = $this->getModel()->getTestingDatasetStatus($row['sid'], $row['enabled']);
            $row['action'] = $this->getModel()->getTestingDatasetAction($row['sid'], $row['action']);
            //
            if (isset($row['reference']) && $row['reference'] != '') {
                // browser friendly reference data
                $row['reference_html'] = '';
                foreach (explode("\n", $row['reference']) as $ref) {
                    $ref = trim($ref);
                    $item_html = '<small><a href="%url%" target="_blank">%ref%</a></small>';
                    if (substr($ref, 0, 4) == 'url,') {
                        $item_html = str_replace("%url%", 'http://' . substr($ref, 4), $item_html);
                        $item_html = str_replace("%ref%", substr($ref, 4), $item_html);
                    } elseif (substr($ref, 0, 7) == "system,") {
                        $item_html = str_replace("%url%", substr($ref, 7), $item_html);
                        $item_html = str_replace("%ref%", substr($ref, 7), $item_html);
                    } elseif (substr($ref, 0, 8) == "bugtraq,") {
                        $item_html = str_replace("%url%", "http://www.securityfocus.com/bid/" .
                            substr($ref, 8), $item_html);
                        $item_html = str_replace("%ref%", "bugtraq " . substr($ref, 8), $item_html);
                    } elseif (substr($ref, 0, 4) == "cve,") {
                        $item_html = str_replace("%url%", "http://cve.mitre.org/cgi-bin/cvename.cgi?name=" .
                            substr($ref, 4), $item_html);
                        $item_html = str_replace("%ref%", substr($ref, 4), $item_html);
                    } elseif (substr($ref, 0, 7) == "nessus,") {
                        $item_html = str_replace("%url%", "http://cgi.nessus.org/plugins/dump.php3?id=" .
                            substr($ref, 7), $item_html);
                        $item_html = str_replace("%ref%", 'nessus ' . substr($ref, 7), $item_html);
                    } elseif (substr($ref, 0, 7) == "mcafee,") {
                        $item_html = str_replace("%url%", "http://vil.nai.com/vil/dispVirus.asp?virus_k=" .
                            substr($ref, 7), $item_html);
                        $item_html = str_replace("%ref%", 'macafee ' . substr($ref, 7), $item_html);
                    } else {
                        continue;
                    }
                    $row['reference_html'] .= $item_html . '<br/>';
                }
            }
            ksort($row);
            return $row;
        } else {
            return array();
        }
    }

    /**
     * List available rule metadata
     * @return array
     * @throws \Exception when configd action fails
     */
    public function listDatasetMetadataAction()
    {
        $this->sessionClose();
        $response = (new Backend())->configdRun("anomaly list datasetmetadata");
        $data = json_decode($response, true);
        if ($data != null) {
            return $data;
        } else {
            return array();
        }
    }

    /**
     * Toggle rule enable status
     * @param string $sids unique id
     * @param string|int $enabled desired state enabled(1)/disabled(1), leave empty for toggle
     * @return array empty
     * @throws \Exception when configd action fails
     * @throws \Phalcon\Validation\Exception when field validations fail
     * @throws \ReflectionException when not bound to model
     */
    public function toggleDatasetAction($sids, $enabled = null)
    {
        if ($this->request->isPost()) {
            $this->sessionClose();
            $update_count = 0;
            foreach (explode(",", $sids) as $sid) {
                $ruleinfo = $this->getDatasetInfoAction($sid);
                $current_action = null;
                foreach ($ruleinfo['action'] as $key => $act) {
                    if (!empty($act['selected'])) {
                        $current_action = $key;
                    }
                }
                if (!empty($ruleinfo)) {
                    if ($enabled == null) {
                        // toggle state
                        if ($ruleinfo['enabled'] == 1) {
                            $new_state = 0;
                        } else {
                            $new_state = 1;
                        }
                    } elseif ($enabled == 1) {
                        $new_state = 1;
                    } elseif ($enabled == "alert") {
                        $current_action = "alert";
                        $new_state = 1;
                    } elseif ($enabled == "drop") {
                        $current_action = "drop";
                        $new_state = 1;
                    } else {
                        $new_state = 0;
                    }
                    if ($ruleinfo['enabled_default'] == $new_state && $current_action == $ruleinfo['action_default']) {
                        // if we're switching back to default, remove alter rule
                        $this->getModel()->removeTestingDataset($sid);
                    } elseif ($new_state == 1) {
                        $this->getModel()->enableTestingDataset($sid)->action = $current_action;
                    } else {
                        $this->getModel()->disableTestingDataset($sid)->action = $current_action;
                    }
                    $update_count++;
                }
            }
            if ($update_count > 0) {
                return $this->save();
            }
        }
        return array();
    }

}
