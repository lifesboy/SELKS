<?php

namespace Selks\Anomaly;

/**
 * Class TensorboardController
 * @package OPNsense\Anomaly
 */
class LocustController extends \OPNsense\Base\IndexController
{
    public function indexAction()
    {
        $this->view->pick('Selks/Anomaly/locust');
    }
}
