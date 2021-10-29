

<p><strong><?= $lang->_('Are you sure you want to reboot the system?') ?></strong></p>

<button id="do-reboot" class="btn btn-primary"><?= $lang->_('Yes') ?></button>
<a href="/" class="btn btn-default"><?= $lang->_('No') ?></a>

<script>
    'use strict';

    function rebootWait() {
        $.ajax({
            url: '/',
            timeout: 2500
        }).fail(function () {
            setTimeout(rebootWait, 2500);
        }).done(function () {
            $(location).attr('href', '/');
        });
    }

    $(document).ready(function() {
        $('#do-reboot').on('click', function() {
            BootstrapDialog.show({
                type:BootstrapDialog.TYPE_INFO,
                title: '<?= $lang->_('Your device is rebooting') ?>',
                closable: false,
                onshow: function(dialogRef){
                    dialogRef.getModalBody().html(
                        '<?= $lang->_('The system is rebooting now, please wait...') ?>' +
                        ' <i class="fa fa-cog fa-spin"></i>'
                );
                    ajaxCall('/api/core/system/reboot');
                    setTimeout(rebootWait, 45000);
                },
            });
        });
    });
</script>
