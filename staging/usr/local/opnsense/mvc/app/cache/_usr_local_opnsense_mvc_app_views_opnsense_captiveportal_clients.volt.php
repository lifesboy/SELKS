
<script src="<?= view_cache_safe('/ui/js/moment-with-locales.min.js') ?>"></script>

<script>

    $( document ).ready(function() {
        /**
         * update zone list
         */
        function updateZones() {
            ajaxGet("/api/captiveportal/session/zones/", {}, function(data, status) {
                if (status == "success") {
                    $('#cp-zones').html("");
                    $.each(data, function(key, value) {
                        $('#cp-zones').append($("<option></option>").attr("value", key).text(value));
                    });
                    $('.selectpicker').selectpicker('refresh');
                    // link on change event
                    $('#cp-zones').on('change', function(){
                        loadSessions();
                    });
                    // initial load sessions
                    loadSessions();
                }
            });
        }

        /**
         * load sessions for selected zone, hook events
         */
        function loadSessions() {
            var zoneid = $('#cp-zones').find("option:selected").val();
            var gridopt = {
                ajax: false,
                selection: true,
                multiSelect: true,
                formatters: {
                    "commands": function (column, row) {
                        return  "<button type=\"button\" class=\"btn btn-xs btn-default command-disconnect\" data-row-id=\"" + row.sessionid + "\"><span class=\"fa fa-trash-o\"></span></button>";
                    }
                }
            };
            $("#grid-clients").bootgrid('destroy');
            ajaxGet("/api/captiveportal/session/list/"+zoneid+"/", {}, function(data, status) {
                if (status == "success") {
                    $("#grid-clients > tbody").html('');
                    $.each(data, function(key, value) {
                        var fields = ["sessionId", "userName", "macAddress", "ipAddress", "startTime"];
                        let tr_str = '<tr>';
                        for (var i = 0; i < fields.length; i++) {
                            if (value[fields[i]] != null) {
                                tr_str += '<td>' + value[fields[i]] + '</td>';
                            } else {
                                tr_str += '<td></td>';
                            }
                        }
                        tr_str += '</tr>';
                        $("#grid-clients > tbody").append(tr_str);
                    });
                    // hook disconnect button
                    var grid_clients = $("#grid-clients").bootgrid(gridopt);
                    grid_clients.on("loaded.rs.jquery.bootgrid", function(){
                        grid_clients.find(".command-disconnect").on("click", function(e) {
                            var sessionId=$(this).data("row-id");
                            stdDialogConfirm('<?= $lang->_('Confirm disconnect') ?>',
                                '<?= $lang->_('Do you want to disconnect the selected client?') ?>',
                                '<?= $lang->_('Yes') ?>', '<?= $lang->_('Cancel') ?>', function () {
                                ajaxCall("/api/captiveportal/session/disconnect/" + zoneid + '/',
                                      {'sessionId': sessionId}, function(data,status){
                                    // reload grid after delete
                                    loadSessions();
                                });
                            });
                        });
                    });
                    // hide actionBar on mobile
                    $('.actionBar').addClass('hidden-xs hidden-sm');
                }
            });
        }

        // init with first selected zone
        updateZones();
    });
</script>

<div class="content-box">
    <div class="content-box-main">
        <div class="table-responsive">
            <div class="col-sm-12">
                <div class="pull-right">
                    <select id="cp-zones" class="selectpicker" data-width="200px"></select>
                    <hr/>
                </div>
            </div>
            <div>
            <table id="grid-clients" class="table table-condensed table-hover table-striped table-responsive">
                <thead>
                <tr>
                    <th data-column-id="sessionid" data-type="string" data-identifier="true" data-visible="false"><?= $lang->_('Session') ?></th>
                    <th data-column-id="userName" data-type="string"><?= $lang->_('Username') ?></th>
                    <th data-column-id="macAddress" data-type="string" data-css-class="hidden-xs hidden-sm" data-header-css-class="hidden-xs hidden-sm"><?= $lang->_('MAC address') ?></th>
                    <th data-column-id="ipAddress" data-type="string" data-css-class="hidden-xs hidden-sm" data-header-css-class="hidden-xs hidden-sm"><?= $lang->_('IP address') ?></th>
                    <th data-column-id="startTime" data-type="datetime"><?= $lang->_('Connected since') ?></th>
                    <th data-column-id="commands" data-width="7em" data-formatter="commands" data-sortable="false"><?= $lang->_('Commands') ?></th>
                </tr>
                </thead>
                <tbody>
                </tbody>
                <tfoot>
                </tfoot>
            </table>
            </div>
        </div>
    </div>
</div>
