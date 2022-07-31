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

use OPNsense\Base\ApiMutableServiceControllerBase;
use OPNsense\Base\Filters\QueryFilter;
use OPNsense\Core\Backend;
use OPNsense\Core\Config;
use OPNsense\Cron\Cron;
use Selks\Anomaly\Anomaly;
use Phalcon\Filter;

/**
 * Class DataProcessorServiceController
 * @package Selks\Anomaly
 */
class TestingServiceController extends ApiMutableServiceControllerBase
{
    protected static $internalServiceClass = '\Selks\Anomaly\Anomaly';
    protected static $internalServiceEnabled = 'testing.enabled';
    protected static $internalServiceTemplate = 'Selks/Anomaly';
    protected static $internalServiceName = 'anomaly';

    /**
     * Reconfigure Anomaly Data Processor
     * @return array result status
     * @throws \Exception when configd action fails
     * @throws \OPNsense\Base\ModelException when unable to construct model
     * @throws \Phalcon\Validation\Exception when one or more model validations fail
     */
    public function reconfigureAction()
    {
        $status = "failed";
        if ($this->request->isPost()) {
            // close session for long running action
            $this->sessionClose();
            $mdlAnomaly = new Anomaly();
            $runStatus = $this->statusAction();
            $runCommand = sprintf("anomaly testing start %s %s",
                $mdlAnomaly->testing->ServingUrl,
                $mdlAnomaly->testing->DataSource);

            // we should always have a cron item configured for Anomaly, let's create one upon first reconfigure.
            if ((string)$mdlAnomaly->testing->UpdateCron == "") {
                $mdlCron = new Cron();
                // update cron relation (if this doesn't break consistency)
                $mdlAnomaly->testing->UpdateCron = $mdlCron->newDailyJob("AnomalyTesting", "anomaly testing start", "anomaly testing updates", "*", "0");

                if ($mdlCron->performValidation()->count() == 0) {
                    $mdlCron->serializeToConfig();
                    // save data to config, do not validate because the current in memory model doesn't know about the
                    // cron item just created.
                    $mdlAnomaly->serializeToConfig($validateFullModel = false, $disable_validation = true);
                    Config::getInstance()->save();
                }
            }

//             if ($runStatus['status'] == "running" && (string)$mdlAnomaly->dataProcessor->enabled == 0) {
//                 $this->stopAction();
//             }

            $backend = new Backend();
            $bckresult = trim($backend->configdRun('template reload Selks/Anomaly'));

            if ($bckresult == "OK") {
                if ((string)$mdlAnomaly->testing->enabled == 1) {
                    $bckresult = trim($backend->configdRun($runCommand, true));
                    if ($bckresult != null) {
                        $status ="ok";
                    } else {
                        $status = "error running testing anomaly model (" . $bckresult . ")";
                    }
                } else {
                    $status = "OK";
                }
            } else {
                $status = "error generating anomaly testing template (" . $bckresult . ")";
            }
        }
        return array("status" => $status);
    }
}
