<?php

namespace Selks\Anomaly;

/**
 * Class RedirectController
 * @package OPNsense\Anomaly
 */
class RedirectController extends \OPNsense\Base\IndexController
{
    public function indexAction()
    {
        $url = $this->request->get("url");
        $this->response->redirect($url, true);
    }
}
