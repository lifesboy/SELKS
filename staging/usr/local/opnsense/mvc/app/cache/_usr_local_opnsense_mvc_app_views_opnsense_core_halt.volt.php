

<p><strong><?= $lang->_('Are you sure you want to power off the system?') ?></strong></p>

<button id="do-halt" class="btn btn-primary"><?= $lang->_('Yes') ?></button>
<a href="/" class="btn btn-default"><?= $lang->_('No') ?></a>

<script>
    'use strict';

    $(document).ready(function() {
        $('#do-halt').on('click', function() {
            BootstrapDialog.show({
                type:BootstrapDialog.TYPE_INFO,
                title: '<?= $lang->_('Your device is powering off') ?>',
                closable: false,
                onshow: function(dialogRef){
                    dialogRef.getModalBody().html('<?= $lang->_('The system is powering off now.') ?>');
                    ajaxCall('/api/core/system/halt');
                },
            });
        });
    });
</script>
