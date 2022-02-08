<?php

/**
 *    Copyright (C) 2015 Deciso B.V.
 *
 *    All rights reserved.
 *
 *    Redistribution and use in source and binary forms, with or without
 *    modification, are permitted provided that the following conditions are met:
 *
 *    1. Redistributions of source code must retain the above copyright notice,
 *       this list of conditions and the following disclaimer.
 *
 *    2. Redistributions in binary form must reproduce the above copyright
 *       notice, this list of conditions and the following disclaimer in the
 *       documentation and/or other materials provided with the distribution.
 *
 *    THIS SOFTWARE IS PROVIDED ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES,
 *    INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY
 *    AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
 *    AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
 *    OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 *    SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 *    INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
 *    CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 *    ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 *    POSSIBILITY OF SUCH DAMAGE.
 *
 */

namespace Selks\Anomaly;

use OPNsense\Base\BaseModel;

/**
 * Class Anomaly
 * @package Selks\Anomaly
 */
class Anomaly extends BaseModel
{
    /**
     * @var array internal list of all sid's in this object
     */
    private $sid_list = array();
    private $sid_list_preprocessing = array();
    private $sid_list_training = array();
    private $sid_list_testing = array();

    /**
     * @var array internal list of all known actions (key/value)
     */
    private $action_list = array();
    private $action_list_preprocessing = array();
    private $action_list_training = array();
    private $action_list_testing = array();

    /**
     * update internal cache of sid's and actions
     */
    private function updateSIDlist()
    {
        if (count($this->sid_list) == 0) {
            foreach ($this->rules->rule->iterateItems() as $NodeKey => $NodeValue) {
                $this->sid_list[$NodeValue->sid->__toString()] = $NodeValue;
            }
            // list of known actions and defaults
            $this->action_list = $this->rules->rule->getTemplateNode()->action->getNodeData();
        }
    }

    private function updatePreprocessingSIDlist()
    {
        if (count($this->sid_list_preprocessing) == 0) {
            foreach ($this->preprocessingDatasets->dataset->iterateItems() as $NodeKey => $NodeValue) {
                $this->sid_list_preprocessing[$NodeValue->sid->__toString()] = $NodeValue;
            }
            // list of known actions and defaults
            $this->action_list_preprocessing = $this->preprocessingDatasets->dataset->getTemplateNode()->action->getNodeData();
        }
    }

    private function updateTrainingSIDlist()
    {
        if (count($this->sid_list_training) == 0) {
            foreach ($this->trainingDatasets->dataset->iterateItems() as $NodeKey => $NodeValue) {
                $this->sid_list_training[$NodeValue->sid->__toString()] = $NodeValue;
            }
            // list of known actions and defaults
            $this->action_list_training = $this->trainingDatasets->dataset->getTemplateNode()->action->getNodeData();
        }
    }

    private function updateTestingSIDlist()
    {
        if (count($this->sid_list_testing) == 0) {
            foreach ($this->testingDatasets->dataset->iterateItems() as $NodeKey => $NodeValue) {
                $this->sid_list_testing[$NodeValue->sid->__toString()] = $NodeValue;
            }
            // list of known actions and defaults
            $this->action_list_testing = $this->testingDatasets->dataset->getTemplateNode()->action->getNodeData();
        }
    }

    /**
     * get new or existing rule
     * @param string $sid unique id
     * @return mixed
     */
    private function getRule($sid)
    {
        $this->updateSIDlist();
        if (!array_key_exists($sid, $this->sid_list)) {
            $rule = $this->rules->rule->Add();
            $rule->sid = $sid;
            $this->sid_list[$sid] = $rule;
        }
        return $this->sid_list[$sid];
    }

    /**
     * get new or existing rule
     * @param string $sid unique id
     * @return mixed
     */
    private function getPreprocessingDataset($sid)
    {
        $this->updatePreprocessingSIDlist();
        if (!array_key_exists($sid, $this->sid_list_preprocessing)) {
            $rule = $this->preprocessingDatasets->dataset->Add();
            $rule->sid = $sid;
            $this->sid_list_preprocessing[$sid] = $rule;
        }
        return $this->sid_list_preprocessing[$sid];
    }

    private function getTrainingDataset($sid)
    {
        $this->updateTrainingSIDlist();
        if (!array_key_exists($sid, $this->sid_list_training)) {
            $rule = $this->trainingDatasets->dataset->Add();
            $rule->sid = $sid;
            $this->sid_list_training[$sid] = $rule;
        }
        return $this->sid_list_training[$sid];
    }

    private function getTestingDataset($sid)
    {
        $this->updateTestingSIDlist();
        if (!array_key_exists($sid, $this->sid_list_testing)) {
            $rule = $this->testingDatasets->dataset->Add();
            $rule->sid = $sid;
            $this->sid_list_testing[$sid] = $rule;
        }
        return $this->sid_list_testing[$sid];
    }

    public function updatePreprocessingDataSource()
    {
        $this->dataProcessor->DataSource = array_map(
            function ($i) { return $i->artifact->__toString(); },
            array_filter($this->sid_list_preprocessing, function ($i) { return '1' === $i->enabled->__toString(); })
        ).join(',');
    }

    /**
     * enable rule
     * @param string $sid unique id
     * @return ArrayField affected rule
     */
    public function enableRule($sid)
    {
        $rule = $this->getRule($sid);
        $rule->enabled = "1";
        return $rule;
    }

    /**
     * enable rule
     * @param string $sid unique id
     * @return ArrayField affected rule
     */
    public function enablePreprocessingDataset($sid)
    {
        $rule = $this->getPreprocessingDataset($sid);
        $rule->enabled = "1";
        return $rule;
    }

    public function enableTrainingDataset($sid)
    {
        $rule = $this->getTrainingDataset($sid);
        $rule->enabled = "1";
        return $rule;
    }

    public function enableTestingDataset($sid)
    {
        $rule = $this->getTestingDataset($sid);
        $rule->enabled = "1";
        return $rule;
    }

    /**
     * disable rule
     * @param string $sid unique id
     * @return ArrayField affected rule
     */
    public function disableRule($sid)
    {
        $rule = $this->getRule($sid);
        $rule->enabled = "0";
        return $rule;
    }

    public function disablePreprocessingDataset($sid)
    {
        $rule = $this->getPreprocessingDataset($sid);
        $rule->enabled = "0";
        return $rule;
    }

    public function disableTrainingDataset($sid)
    {
        $rule = $this->getTrainingDataset($sid);
        $rule->enabled = "0";
        return $rule;
    }

    public function disableTestingDataset($sid)
    {
        $rule = $this->getTestingDataset($sid);
        $rule->enabled = "0";
        return $rule;
    }

    /**
     * set new action for selected rule
     * @param string $sid unique id
     * @param $action
     */
    public function setAction($sid, $action)
    {
        $rule = $this->getRule($sid);
        $rule->action = $action;
    }

    /**
     * remove rule by sid
     * @param string $sid unique id
     */
    public function removeRule($sid)
    {
        // search and drop rule
        foreach ($this->rules->rule->iterateItems() as $NodeKey => $NodeValue) {
            if ((string)$NodeValue->sid == $sid) {
                $this->rules->rule->Del($NodeKey);
                unset($this->sid_list[$sid]);
                break;
            }
        }
    }

    /**
     * remove rule by sid
     * @param string $sid unique id
     */
    public function removePreprocessingDataset($sid)
    {
        // search and drop rule
        foreach ($this->preprocessingDatasets->dataset->iterateItems() as $NodeKey => $NodeValue) {
            if ((string)$NodeValue->sid == $sid) {
                $this->preprocessingDatasets->dataset->Del($NodeKey);
                unset($this->sid_list_preprocessing[$sid]);
                break;
            }
        }
    }

    public function removeTrainingDataset($sid)
    {
        // search and drop rule
        foreach ($this->trainingDatasets->dataset->iterateItems() as $NodeKey => $NodeValue) {
            if ((string)$NodeValue->sid == $sid) {
                $this->trainingDatasets->dataset->Del($NodeKey);
                unset($this->sid_list_training[$sid]);
                break;
            }
        }
    }

    public function removeTestingDataset($sid)
    {
        // search and drop rule
        foreach ($this->testingDatasets->dataset->iterateItems() as $NodeKey => $NodeValue) {
            if ((string)$NodeValue->sid == $sid) {
                $this->testingDatasets->dataset->Del($NodeKey);
                unset($this->sid_list_testing[$sid]);
                break;
            }
        }
    }

    /**
     * retrieve current altered rule status
     * @param string $sid unique id
     * @param string $default default value
     * @return string|bool default, 0, 1 ( default, true, false)
     */
    public function getRuleStatus($sid, $default)
    {
        $this->updateSIDlist();
        if (!empty($sid) && array_key_exists($sid, $this->sid_list)) {
            return (string)$this->sid_list[$sid]->enabled;
        } else {
            return $default;
        }
    }

    public function getPreprocessingDatasetStatus($sid, $default)
    {
        $this->updatePreprocessingSIDlist();
        if (!empty($sid) && array_key_exists($sid, $this->sid_list_preprocessing)) {
            return (string)$this->sid_list_preprocessing[$sid]->enabled;
        } else {
            return $default;
        }
    }

    public function getTrainingDatasetStatus($sid, $default)
    {
        $this->updateTrainingSIDlist();
        if (!empty($sid) && array_key_exists($sid, $this->sid_list_training)) {
            return (string)$this->sid_list_training[$sid]->enabled;
        } else {
            return $default;
        }
    }

    public function getTestingDatasetStatus($sid, $default)
    {
        $this->updateTestingSIDlist();
        if (!empty($sid) && array_key_exists($sid, $this->sid_list_testing)) {
            return (string)$this->sid_list_testing[$sid]->enabled;
        } else {
            return $default;
        }
    }

    /**
     * retrieve current (altered) rule action
     * @param string $sid unique id
     * @param string $default default value
     * @param bool $response_plain response as text ot model (select list)
     * @return string|bool default, <action value> ( default, true, false)
     */
    public function getRuleAction($sid, $default, $response_plain = false)
    {
        $this->updateSIDlist();
        if (!empty($sid) && array_key_exists($sid, $this->sid_list)) {
            if (!$response_plain) {
                return $this->sid_list[$sid]->action->getNodeData();
            } else {
                $act = (string)$this->sid_list[$sid]->action;
                if (array_key_exists($act, $this->action_list)) {
                    return $this->action_list[$act]['value'];
                } else {
                    return $act;
                }
            }
        } elseif (!$response_plain) {
            // generate selection for new field
            $default_types = $this->action_list;
            if (array_key_exists($default, $default_types)) {
                foreach ($default_types as $key => $value) {
                    if ($key ==  $default) {
                        $default_types[$key]['selected'] = 1;
                    } else {
                        $default_types[$key]['selected'] = 0;
                    }
                }
            }
            // select default
            return $default_types;
        } else {
            // return plaintext default
            if (array_key_exists($default, $this->action_list)) {
                return $this->action_list[$default]['value'];
            } else {
                return $default;
            }
        }
    }

    public function getPreprocessingDatasetAction($sid, $default, $response_plain = false)
    {
        $this->updatePreprocessingSIDlist();
        if (!empty($sid) && array_key_exists($sid, $this->sid_list_preprocessing)) {
            if (!$response_plain) {
                return $this->sid_list_preprocessing[$sid]->action->getNodeData();
            } else {
                $act = (string)$this->sid_list_preprocessing[$sid]->action;
                if (array_key_exists($act, $this->action_list_preprocessing)) {
                    return $this->action_list_preprocessing[$act]['value'];
                } else {
                    return $act;
                }
            }
        } elseif (!$response_plain) {
            // generate selection for new field
            $default_types = $this->action_list_preprocessing;
            if (array_key_exists($default, $default_types)) {
                foreach ($default_types as $key => $value) {
                    if ($key ==  $default) {
                        $default_types[$key]['selected'] = 1;
                    } else {
                        $default_types[$key]['selected'] = 0;
                    }
                }
            }
            // select default
            return $default_types;
        } else {
            // return plaintext default
            if (array_key_exists($default, $this->action_list_preprocessing)) {
                return $this->action_list_preprocessing[$default]['value'];
            } else {
                return $default;
            }
        }
    }

    public function getTrainingDatasetAction($sid, $default, $response_plain = false)
    {
        $this->updateTrainingSIDlist();
        if (!empty($sid) && array_key_exists($sid, $this->sid_list_training)) {
            if (!$response_plain) {
                return $this->sid_list_training[$sid]->action->getNodeData();
            } else {
                $act = (string)$this->sid_list_training[$sid]->action;
                if (array_key_exists($act, $this->action_list_training)) {
                    return $this->action_list_training[$act]['value'];
                } else {
                    return $act;
                }
            }
        } elseif (!$response_plain) {
            // generate selection for new field
            $default_types = $this->action_list_training;
            if (array_key_exists($default, $default_types)) {
                foreach ($default_types as $key => $value) {
                    if ($key ==  $default) {
                        $default_types[$key]['selected'] = 1;
                    } else {
                        $default_types[$key]['selected'] = 0;
                    }
                }
            }
            // select default
            return $default_types;
        } else {
            // return plaintext default
            if (array_key_exists($default, $this->action_list_training)) {
                return $this->action_list_training[$default]['value'];
            } else {
                return $default;
            }
        }
    }

    public function getTestingDatasetAction($sid, $default, $response_plain = false)
    {
        $this->updateTestingSIDlist();
        if (!empty($sid) && array_key_exists($sid, $this->sid_list_testing)) {
            if (!$response_plain) {
                return $this->sid_list_testing[$sid]->action->getNodeData();
            } else {
                $act = (string)$this->sid_list_testing[$sid]->action;
                if (array_key_exists($act, $this->action_list_testing)) {
                    return $this->action_list_testing[$act]['value'];
                } else {
                    return $act;
                }
            }
        } elseif (!$response_plain) {
            // generate selection for new field
            $default_types = $this->action_list_testing;
            if (array_key_exists($default, $default_types)) {
                foreach ($default_types as $key => $value) {
                    if ($key ==  $default) {
                        $default_types[$key]['selected'] = 1;
                    } else {
                        $default_types[$key]['selected'] = 0;
                    }
                }
            }
            // select default
            return $default_types;
        } else {
            // return plaintext default
            if (array_key_exists($default, $this->action_list_testing)) {
                return $this->action_list_testing[$default]['value'];
            } else {
                return $default;
            }
        }
    }

    /**
     * retrieve (rule) file entry from config or add a new one
     * @param string $filename list of filename to merge into config
     * @return BaseField number of appended items
     */
    public function getFileNode($filename)
    {
        foreach ($this->files->file->iterateItems() as $NodeKey => $NodeValue) {
            if ($filename == $NodeValue->filename) {
                return $NodeValue;
            }
        }
        // add a new node
        $node = $this->files->file->Add();
        $node->filename = $filename;

        return $node;
    }
}
