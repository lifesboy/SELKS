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

/**
 * Class IndexController
 * @package OPNsense\IDS
 */
class IndexController extends \OPNsense\Base\IndexController
{
    /**
     * default anomaly index page
     * @throws \Exception
     */
    public function indexAction()
    {
        // link rule dialog
        $this->view->formDialogRule = $this->getForm("dialogRule");
        // link Anomaly general settings
        $this->view->formGeneralSettings = $this->getForm("generalSettings");
        // link Anomaly data processor settings
        $this->view->formDataProcessorSettings = $this->getForm("dataProcessorSettings");
        $this->view->formLabelingSettings = $this->getForm("labelingSettings");
        $this->view->formInferringSettings = $this->getForm("inferringSettings");
        // link alert list dialog
        $this->view->formDialogRuleset = $this->getForm("dialogRuleset");
        // link fingerprint dialog
        $this->view->formDialogUserDefined = $this->getForm("dialogUserDefined");
        // choose template
        $this->view->pick('Selks/Anomaly/index');
    }
}
