<?php

namespace Selks\Anomaly;

/**
 * Class TensorboardController
 * @package OPNsense\Anomaly
 */
class TensorboardController extends \OPNsense\Base\IndexController
{
    public function indexAction()
    {
        $this->view->pick('Selks/Anomaly/tensorboard');
    }
}
