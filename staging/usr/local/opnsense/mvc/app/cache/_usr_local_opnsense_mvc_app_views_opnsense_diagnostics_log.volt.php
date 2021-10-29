

<script>
    $( document ).ready(function() {
      $("#grid-log").UIBootgrid({
          options:{
              sorting:false,
              rowSelect: false,
              selection: false,
              rowCount:[20,50,100,200,500,1000,-1],
          },
          search:'/api/diagnostics/log/<?= $module ?>/<?= $scope ?>'
      });

      $("#flushlog").on('click', function(event){
        event.preventDefault();
        BootstrapDialog.show({
          type: BootstrapDialog.TYPE_DANGER,
          title: "<?= $lang->_('Log') ?>",
          message: "<?= $lang->_('Do you really want to flush this log?') ?>",
          buttons: [{
            label: "<?= $lang->_('No') ?>",
            action: function(dialogRef) {
              dialogRef.close();
            }}, {
              label: "<?= $lang->_('Yes') ?>",
              action: function(dialogRef) {
                  ajaxCall("/api/diagnostics/log/<?= $module ?>/<?= $scope ?>/clear", {}, function(){
                      dialogRef.close();
                      $('#grid-log').bootgrid('reload');
                  });
              }
            }]
        });
      });
      // download (filtered) items
      $("#exportbtn").click(function(event){
          let download_link = "/api/diagnostics/log/<?= $module ?>/<?= $scope ?>/export";
          if ($("input.search-field").val() !== "") {
              download_link = download_link + "?searchPhrase=" + encodeURIComponent($("input.search-field").val());
          }
          $('<a></a>').attr('href',download_link).get(0).click();
      });

    });
</script>

<div class="content-box">
    <div class="content-box-main">
        <div class="table-responsive">
            <div  class="col-sm-12">
                <table id="grid-log" class="table table-condensed table-hover table-striped table-responsive" data-store-selection="true">
                    <thead>
                    <tr>
                        <th data-column-id="pos" data-type="numeric" data-identifier="true"  data-visible="false">#</th>
                        <th data-column-id="timestamp" data-width="11em" data-type="string"><?= $lang->_('Date') ?></th>
                        <th data-column-id="line" data-type="string"><?= $lang->_('Line') ?></th>
                    </tr>
                    </thead>
                    <tbody>
                    </tbody>
                    <tfoot>
                      <td></td>
                      <td>
                        <button id="exportbtn"
                            data-toggle="tooltip" title="" type="button"
                            class="btn btn-xs btn-default pull-right"
                            data-original-title="<?= $lang->_('download selection') ?>">
                            <span class="fa fa-cloud-download"></span>
                        </button>
                      </td>
                    </tfoot>
                </table>
                <table class="table">
                    <tbody>
                        <tr>
                            <td>
                              <button class="btn btn-primary pull-right" id="flushlog">
                                  <?= $lang->_('Clear log') ?>
                              </button>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>
