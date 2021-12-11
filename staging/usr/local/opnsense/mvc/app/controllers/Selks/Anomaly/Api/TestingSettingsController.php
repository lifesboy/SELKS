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
}
