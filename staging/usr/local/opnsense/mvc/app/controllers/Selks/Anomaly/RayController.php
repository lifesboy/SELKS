<?php

namespace Selks\Anomaly;

/**
 * Class TensorboardController
 * @package OPNsense\Anomaly
 */
class RayController extends \OPNsense\Base\IndexController
{
    public function indexAction()
    {
        $this->view->pick('Selks/Anomaly/ray');
    }
}
