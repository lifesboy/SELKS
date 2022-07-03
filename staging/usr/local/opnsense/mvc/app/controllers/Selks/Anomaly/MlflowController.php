<?php

namespace Selks\Anomaly;

/**
 * Class TensorboardController
 * @package OPNsense\Anomaly
 */
class MlflowController extends \OPNsense\Base\IndexController
{
    public function indexAction()
    {
        $this->view->pick('Selks/Anomaly/mlflow');
    }
}
