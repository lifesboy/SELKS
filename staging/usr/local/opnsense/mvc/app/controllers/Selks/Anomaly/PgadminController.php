<?php

namespace Selks\Anomaly;

/**
 * Class TensorboardController
 * @package OPNsense\Anomaly
 */
class PgadminController extends \OPNsense\Base\IndexController
{
    public function indexAction()
    {
        $this->view->pick('Selks/Anomaly/pgadmin');
    }
}
