{#

OPNsense® is Copyright © 2014 – 2015 by Deciso B.V.
All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

1.  Redistributions of source code must retain the above copyright notice,
this list of conditions and the following disclaimer.

2.  Redistributions in binary form must reproduce the above copyright notice,
this list of conditions and the following disclaimer in the documentation
and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED “AS IS” AND ANY EXPRESS OR IMPLIED WARRANTIES,
INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY
AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.

#}
<style>
    .tooltip-inner {
        min-width: 250px;
    }

    .anomaly-alert-info > tbody > tr > td {
        padding-top: 2px !important;
        padding-bottom: 2px !important;
    }
    .anomaly-alert-info > tbody > tr > td:first-child {
        width: 150px;
    }
    @media (min-width: 768px) {
        .suricata-alert > .modal-dialog {
            width: 90%;
            max-width:1200px;
        }
    }
</style>

<script>

    $( document ).ready(function() {
        var interface_descriptions = {};
        //
        var data_get_map = {'frm_GeneralSettings':"/api/anomaly/settings/get"};
        //
        var data_processor_settings_get_map = {'frm_DataProcessorSettings':"/api/anomaly/data-processor-settings/get"};

        //
        var labeling_settings_get_map = {'frm_LabelingSettings':"/api/anomaly/labeling-settings/get"};

        //
        var inferring_settings_get_map = {'frm_InferringSettings':"/api/anomaly/inferring-settings/get"};

        /**
         * update service status
         */
        function updateStatus() {
            updateServiceControlUI('anomaly');
        }

        /**
         * list all known classtypes and add to selection box
         */
        function updateRuleMetadata() {
            ajaxGet("/api/anomaly/settings/listRuleMetadata", {}, function(data, status) {
                if (status == "success") {
                    $('#rulemetadata').empty();
                    $.each(Object.assign({}, {'action': ['drop', 'alert']}, data), function(key, values) {
                        let $optgroup = $("<optgroup/>");
                        $optgroup.prop('label', key);
                        for (let i=0; i < values.length ; ++i) {
                            $optgroup.append(
                              $("<option>").val(values[i]).text(values[i].substr(0, 50))
                                .data('property', key)
                                .data('value', values[i])
                                .data('content', "<span class='badge'>"+key+"\\"+values[i].substr(0, 50)+"</span>")
                            );
                        }
                        $('#rulemetadata').append($optgroup);
                    });
                    $('.selectpicker').selectpicker('refresh');
                    // link on change event
                    $('#rulemetadata').on('change', function(){
                        $('#grid-installedrules').bootgrid('reload');
                    });
                }
            });
        }

        /**
         * update list of available alert logs
         */
        function updateAlertLogs() {
            ajaxGet("/api/anomaly/service/getAlertLogs", {}, function(data, status) {
                if (status == "success") {
                    $('#alert-logfile').html("");
                    $.each(data, function(key, value) {
                        if (value['sequence'] == undefined) {
                            $('#alert-logfile').append($("<option/>").data('filename', value['filename']).attr("value",'none').text(value['modified']));
                        } else {
                            $('#alert-logfile').append($("<option/>").data('filename', value['filename']).attr("value",value['sequence']).text(value['modified']));
                        }
                    });
                    $('.selectpicker').selectpicker('refresh');
                    // link on change event
                    $('#alert-logfile').on('change', function(){
                        $('#grid-alerts').bootgrid('reload');
                    });
                }
            });
        }

        /**
         * Add classtype / action to rule filter
         */
        function addRuleFilters(request) {
            $('#rulemetadata').find("option:selected").each(function(){
                let filter_name = $(this).data('property');
                if (request[filter_name] === undefined) {
                    request[filter_name] = $(this).data('value');
                } else {
                    request[filter_name] += "," + $(this).data('value');
                }
            });
            return request;
        }

        /**
         *  add filter criteria to log query
         */
        function addAlertQryFilters(request) {
            var selected_logfile =$('#alert-logfile').find("option:selected").val();
            var selected_max_entries =$('#alert-logfile-max').find("option:selected").val();
            var search_phrase = $("#inputSearchAlerts").val();

            // add loading overlay
            $('#processing-dialog').modal('show');
            $("#grid-alerts").bootgrid().on("loaded.rs.jquery.bootgrid", function (e){
                $('#processing-dialog').modal('hide');
            });


            if ( selected_logfile != "") {
                request['fileid'] = selected_logfile;
                request['rowCount'] = selected_max_entries;
                request['searchPhrase'] = search_phrase;
            }
            return request;
        }

        // load initial data
        function loadDataProcessorSettings() {
            mapDataToFormUI(data_processor_settings_get_map).done(function(data){
                // set schedule updates link to cron
                $.each(data.frm_DataProcessorSettings.anomaly.dataProcessor.UpdateCron, function(key, value) {
                    if (value.selected == 1) {
                        $("#scheduled_updates_dataprocessor a").attr("href","/ui/cron/item/open/"+key);
                        $("#scheduled_updates_dataprocessor").show();
                    }
                });
                // set schedule updates link to train cron
                $.each(data.frm_DataProcessorSettings.anomaly.dataProcessor.UpdateTrainCron, function(key, value) {
                    if (value.selected == 1) {
                        $("#scheduled_updates_dataprocessorcic a").attr("href","/ui/cron/item/open/"+key);
                        $("#scheduled_updates_dataprocessorcic").show();
                    }
                });
                formatTokenizersUI();
                $('.selectpicker').selectpicker('refresh');
            });
        }

        // load initial data
        function loadLabelingSettings() {
            mapDataToFormUI(labeling_settings_get_map).done(function(data){
                // set schedule updates link to cron
                $.each(data.frm_LabelingSettings.anomaly.labeling.UpdateCron, function(key, value) {
                    if (value.selected == 1) {
                        $("#scheduled_updates_labeling a").attr("href","/ui/cron/item/open/"+key);
                        $("#scheduled_updates_labeling").show();
                    }
                });
            });
        }

        // load initial data
        function loadInferringSettings() {
            mapDataToFormUI(inferring_settings_get_map).done(function(data){
                // set schedule updates link to cron
                $.each(data.frm_InferringSettings.anomaly.inferring.UpdateCron, function(key, value) {
                    if (value.selected == 1) {
                        $("#scheduled_updates_inferring a").attr("href","/ui/cron/item/open/"+key);
                        $("#scheduled_updates_inferring").show();
                    }
                });
            });
        }

        // load initial data
        function loadGeneralSettings() {
            mapDataToFormUI(data_get_map).done(function(data){
                // set schedule updates link to cron
                $.each(data.frm_GeneralSettings.anomaly.general.UpdateCron, function(key, value) {
                    if (value.selected == 1) {
                        $("#scheduled_updates_general a").attr("href","/ui/cron/item/open/"+key);
                        $("#scheduled_updates_general").show();
                    }
                });
            });
        }

        /**
         * toggle selected items
         * @param gridId: grid id to to use
         * @param url: ajax action to call
         * @param state: 0/1/undefined
         * @param combine: number of keys to combine (separate with ,)
         *                 try to avoid too much items per call (results in too long url's)
         */
        function actionToggleSelected(gridId, url, state, combine) {
            var defer_toggle = $.Deferred();
            var rows = $("#"+gridId).bootgrid('getSelectedRows');
            if (rows != undefined){
                var deferreds = [];
                if (state != undefined) {
                    var url_suffix = state;
                } else {
                    var url_suffix = "";
                }
                var base = $.when({});
                var keyset = [];
                $.each(rows, function(key, uuid){
                    // only perform action in visible items
                    if ($("#"+gridId).find("tr[data-row-id='"+uuid+"']").is(':visible')) {
                        keyset.push(uuid);
                        if ( combine === undefined || keyset.length > combine || rows[rows.length - 1] === uuid) {
                            var call_url = url + keyset.join(',') +'/'+url_suffix;
                            base = base.then(function() {
                                var defer = $.Deferred();
                                ajaxCall(call_url, {}, function(){
                                    defer.resolve();
                                });
                                return defer.promise();
                            });
                            keyset = [];
                        }
                    }
                });
                // last action in the list, reload grid and release this promise
                base.then(function(){
                    $("#"+gridId).bootgrid("reload");
                    let changemsg = $("#"+gridId).data("editalert");
                    if (changemsg !== undefined) {
                        $("#"+changemsg).slideDown(1000, function(){
                            setTimeout(function(){
                                $("#"+changemsg).slideUp(2000);
                            }, 2000);
                        });
                    }
                    defer_toggle.resolve();
                });
            } else {
                defer_toggle.resolve();
            }
            return defer_toggle.promise();
        }

        /*************************************************************************************************************
         * UI load grids (on tab change)
         *************************************************************************************************************/

        /**
         * load content on tab changes
         */
        $('a[data-toggle="tab"]').on('shown.bs.tab', function (e) {
            loadGeneralSettings();
            loadLabelingSettings();
            loadInferringSettings();
            loadDataProcessorSettings();

            if (e.target.id == 'training_histories_tab') {
                /**
                 * grid for installable rule files
                 */
                $('#grid-rule-files').bootgrid('destroy'); // always destroy previous grid, so data is always fresh
                $("#grid-rule-files").UIBootgrid({
                    search:'/api/anomaly/settings/listRulesets',
                    get:'/api/anomaly/settings/getRuleset/',
                    set:'/api/anomaly/settings/setRuleset/',
                    toggle:'/api/anomaly/settings/toggleRuleset/',
                    options:{
                        navigation:0,
                        formatters:{
                            editor: function (column, row) {
                                return "<button type=\"button\" class=\"btn btn-xs btn-default command-edit\" data-row-id=\"" + row.filename + "\"><span class=\"fa fa-pencil\"></span></button>";
                            },
                            boolean: function (column, row) {
                                if (parseInt(row[column.id], 2) == 1) {
                                    return "<span class=\"fa fa-check command-boolean\" data-value=\"1\" data-row-id=\"" + row.filename + "\"></span>";
                                } else {
                                    return "<span class=\"fa fa-times command-boolean\" data-value=\"0\" data-row-id=\"" + row.filename + "\"></span>";
                                }
                            }
                        },
                        converters: {
                            // show "not installed" for rules without timestamp (not on disc)
                            rulets: {
                                from: function (value) {
                                    return value;
                                },
                                to: function (value) {
                                    if ( value == null ) {
                                        return "{{ lang._('not installed') }}";
                                    } else {
                                        return value;
                                    }
                                }
                            }
                        }
                    }
                });
                // display file settings (if available)
                ajaxGet("/api/anomaly/settings/getRulesetproperties", {}, function(data, status) {
                    if (status == "success") {
                        var rows = [];
                        // generate rows with field references
                        $.each(data['properties'], function(key, value) {
                            rows.push('<tr><td>'+key+'</td><td><input class="rulesetprop" data-id="'+key+'" type="text"></td></tr>');
                        });
                        $("#grid-rule-files-settings > tbody").html(rows.join(''));
                        // update with data
                        $(".rulesetprop").each(function(){
                            $(this).val(data['properties'][$(this).data('id')]);
                        });
                        if (rows.length > 0) {
                            $("#grid-rule-files-settings").parent().parent().show();
                            $("#updateSettings").show();
                        }
                    }
                });
                /**
                 * disable/enable[with optional filter] selected rulesets
                 */
                $("#disableSelectedRuleSets").unbind('click').click(function(){
                    actionToggleSelected('grid-rule-files', '/api/anomaly/settings/toggleRuleset/', 0, 20);
                });
                $("#enableSelectedRuleSets").unbind('click').click(function(){
                    actionToggleSelected('grid-rule-files', '/api/anomaly/settings/toggleRuleset/', 1, 20);
                });
                $("#enabledropSelectedRuleSets").unbind('click').click(function(){
                    actionToggleSelected('grid-rule-files', '/api/anomaly/settings/toggleRuleset/', "drop", 20);
                });
                $("#enableclearSelectedRuleSets").click(function(){
                    actionToggleSelected('grid-rule-files', '/api/anomaly/settings/toggleRuleset/', "clear", 20);
                });
            } else if (e.target.id == 'rule_tab'){
                //
                // activate rule tab page
                //

                // delay refresh for a bit
                setTimeout(updateRuleMetadata, 500);

                /**
                 * grid installed rules
                 */
                $('#grid-installedrules').bootgrid('destroy'); // always destroy previous grid, so data is always fresh
                $("#grid-installedrules").UIBootgrid(
                        {   search:'/api/anomaly/settings/searchinstalledrules',
                            get:'/api/anomaly/settings/getRuleInfo/',
                            set:'/api/anomaly/settings/setRule/',
                            options:{
                                requestHandler:addRuleFilters,
                                rowCount:[10, 25, 50,100,500,1000] ,
                                formatters:{
                                    rowtoggle: function (column, row) {
                                        var toggle = " <button type=\"button\" class=\"btn btn-xs btn-default command-edit\" data-row-id=\"" + row.sid + "\"><span class=\"fa fa-pencil\"></span></button> ";
                                        if (parseInt(row[column.id], 2) == 1) {
                                            toggle += "&nbsp; <span style=\"cursor: pointer;\" class=\"fa fa-check-square-o command-toggle\" data-value=\"1\" data-row-id=\"" + row.sid + "\"></span>";
                                        } else {
                                            toggle += "&nbsp; <span style=\"cursor: pointer;\" class=\"fa fa-square-o command-toggle\" data-value=\"0\" data-row-id=\"" + row.sid + "\"></span>";
                                        }
                                        return toggle;
                                    }
                                },
                                onBeforeRenderDialog: function(payload) {
                                    // update form with dynamic fields
                                    let template_tr = $("#row___template__");
                                    $(".__rule__metadata_record").remove();
                                    template_tr.hide();
                                    if (payload.frm_DialogRule) {
                                        $.each(payload.frm_DialogRule, function(key, value){
                                            // ignore fixed fields and empty values
                                            if (['sid', 'rev', 'action', 'action_default', 'installed_action',
                                                 'enabled', 'enabled_default', 'msg', 'reference'].includes(key)
                                                 || value === null) {
                                                return;
                                            }
                                            let new_tr = template_tr.clone();
                                            new_tr.prop("id", "row_" + key);
                                            new_tr.addClass("__rule__metadata_record");
                                            new_tr.html(new_tr.html().replace('__template__label__', key));
                                            if (key === 'reference_html') {
                                                value = $("<textarea/>").html(value).text();
                                            }
                                            new_tr.find("#__template__").prop("id", key).html(value);
                                            new_tr.show();
                                            new_tr.insertBefore(template_tr);
                                        });
                                    }
                                    return (new $.Deferred()).resolve();
                                }
                            },
                            toggle:'/api/anomaly/settings/toggleRule/'
                        }
                );
                /**
                 * disable/enable [+action] selected rules
                 */
                $("#disableSelectedRules").unbind('click').click(function(event){
                    event.preventDefault();
                    $("#disableSelectedRules > span").removeClass("fa-square-o").addClass("fa-spinner fa-pulse");
                    actionToggleSelected('grid-installedrules', '/api/anomaly/settings/toggleRule/', 0, 100).done(function(){
                        $("#disableSelectedRules > span").removeClass("fa-spinner fa-pulse");
                        $("#disableSelectedRules > span").addClass("fa-square-o");
                    });
                });
                $("#enableSelectedRules").unbind('click').click(function(){
                    $("#enableSelectedRules > span").removeClass("fa-check-square-o").addClass("fa-spinner fa-pulse");
                    actionToggleSelected('grid-installedrules', '/api/anomaly/settings/toggleRule/', 1, 100).done(function(){
                        $("#enableSelectedRules > span").removeClass("fa-spinner fa-pulse").addClass("fa-check-square-o");
                    });
                });
                $("#alertSelectedRules").unbind('click').click(function(){
                    $("#alertSelectedRules > span").addClass("fa-spinner fa-pulse");
                    actionToggleSelected('grid-installedrules', '/api/anomaly/settings/toggleRule/', "alert", 100).done(function(){
                        $("#alertSelectedRules > span").removeClass("fa-spinner fa-pulse");
                    });
                });
                $("#dropSelectedRules").unbind('click').click(function(){
                    $("#dropSelectedRules > span").addClass("fa-spinner fa-pulse");
                    actionToggleSelected('grid-installedrules', '/api/anomaly/settings/toggleRule/', "drop", 100).done(function(){
                        $("#dropSelectedRules > span").removeClass("fa-spinner fa-pulse");
                    });
                });
            } else if (e.target.id == 'alert_tab') {
                updateAlertLogs();
                /**
                 * grid query alerts
                 */
                $('#grid-alerts').bootgrid('destroy'); // always destroy previous grid, so data is always fresh
                var grid_alerts = $("#grid-alerts").UIBootgrid(
                        {   search:'/api/anomaly/service/queryAlerts',
                            get:'/api/anomaly/service/getAlertInfo/',
                            options:{
                                multiSelect:false,
                                selection:false,
                                templates : {
                                    header: ""
                                },
                                requestHandler:addAlertQryFilters,
                                formatters:{
                                    info: function (column, row) {
                                        return "<button type=\"button\" class=\"btn btn-xs btn-default command-alertinfo\" data-row-id=\"" + row.filepos + "/" + row.fileid + "\"><span class=\"fa fa-pencil\"></span></button> ";
                                    }
                                },
                                converters: {
                                    // convert interface to name
                                    interface: {
                                        from: function (value) { return value; },
                                        to: function (value) {
                                          if (value == null || value == undefined) {
                                              return "";
                                          }
                                          return interface_descriptions[value.replace(/\+$/, '')];
                                        }
                                    }
                                }
                            }
                        });
                // tooltip wide fields in alert grid
                grid_alerts.on("loaded.rs.jquery.bootgrid", function(){
                    $("#grid-alerts > tbody > tr > td").each(function(){
                        if ($(this).outerWidth() < $(this)[0].scrollWidth) {
                            var grid_td = $("<span/>");
                            grid_td.html($(this).html());
                            grid_td.tooltip({title: $(this).text()});
                            $(this).html(grid_td);
                        }
                    });
                });
                // hook in alert details on alertinfo command
                grid_alerts.on("loaded.rs.jquery.bootgrid", function(){
                    grid_alerts.find(".command-alertinfo").on("click", function(e) {
                        var uuid=$(this).data("row-id");
                        ajaxGet('/api/anomaly/service/getAlertInfo/' + uuid, {}, function(data, status) {
                                if (status == 'success') {
                                    ajaxGet("/api/anomaly/settings/getRuleInfo/"+data['alert_sid'], {}, function(rule_data, rule_status) {
                                        var tbl = $('<table class="table table-condensed table-hover anomaly-alert-info"/>');
                                        var tbl_tbody = $("<tbody/>");
                                        var alert_fields = {};
                                        alert_fields['timestamp'] = "{{ lang._('Timestamp') }}";
                                        alert_fields['alert'] = "{{ lang._('Alert') }}";
                                        alert_fields['alert_sid'] = "{{ lang._('Alert sid') }}";
                                        alert_fields['proto'] = "{{ lang._('Protocol') }}";
                                        alert_fields['src_ip'] = "{{ lang._('Source IP') }}";
                                        alert_fields['dest_ip'] = "{{ lang._('Destination IP') }}";
                                        alert_fields['src_port'] = "{{ lang._('Source port') }}";
                                        alert_fields['dest_port'] = "{{ lang._('Destination port') }}";
                                        alert_fields['in_iface'] = "{{ lang._('Interface') }}";
                                        alert_fields['http.hostname'] = "{{ lang._('http hostname') }}";
                                        alert_fields['http.url'] = "{{ lang._('http url') }}";
                                        alert_fields['http.http_user_agent'] = "{{ lang._('http user_agent') }}";
                                        alert_fields['http.http_content_type'] = "{{ lang._('http content_type') }}";
                                        alert_fields['tls.subject'] = "{{ lang._('tls subject') }}";
                                        alert_fields['tls.issuerdn'] = "{{ lang._('tls issuer') }}";
                                        alert_fields['tls.session_resumed'] = "{{ lang._('tls session resumed') }}";
                                        alert_fields['tls.fingerprint'] = "{{ lang._('tls fingerprint') }}";
                                        alert_fields['tls.serial'] = "{{ lang._('tls serial') }}";
                                        alert_fields['tls.version'] = "{{ lang._('tls version') }}";
                                        alert_fields['tls.notbefore'] = "{{ lang._('tls notbefore') }}";
                                        alert_fields['tls.notafter'] = "{{ lang._('tls notafter') }}";

                                        $.each( alert_fields, function( fieldname, fielddesc ) {
                                            var data_ptr = data;
                                            $.each(fieldname.split('.'),function(indx, keypart){
                                                if (data_ptr != undefined) {
                                                    data_ptr = data_ptr[keypart];
                                                }
                                            });

                                            if (data_ptr != undefined) {
                                                var row = $("<tr/>");
                                                row.append($("<td/>").text(fielddesc));
                                                if (fieldname == 'in_iface' && interface_descriptions[data_ptr.replace(/\+$/, '')] != undefined) {
                                                    row.append($("<td/>").text(interface_descriptions[data_ptr.replace(/\+$/, '')]));
                                                } else {
                                                    row.append($("<td/>").text(data_ptr));
                                                }
                                                tbl_tbody.append(row);
                                            }
                                        });

                                        if (rule_data.action != undefined) {
                                            var alert_select = $('<select/>');
                                            var alert_enabled = $('<input type="checkbox"/>');
                                            if (rule_data.enabled == '1') {
                                                alert_enabled.prop('checked', true);
                                            }
                                            $.each(rule_data.action, function(key, value){
                                                var opt = $('<option/>').attr("value", key).text(value.value);
                                                if (value.selected == 1) {
                                                    opt.attr('selected', 'selected');
                                                }
                                                alert_select.append(opt);
                                            });
                                            tbl_tbody.append(
                                              $("<tr/>").append(
                                                $("<td/>").text("{{ lang._('Configured action') }}"),
                                                $("<td id='alert_sid_action'/>").append(
                                                  alert_enabled, $("<span/>").html("&nbsp; <strong>{{lang._('Enabled')}}</strong><br/>"), alert_select, $("<br/>")
                                                )
                                              )
                                            );
                                            alert_select.change(function(){
                                                var rule_params = {'action': alert_select.val()};
                                                if (alert_enabled.is(':checked')) {
                                                    rule_params['enabled'] = 1;
                                                } else {
                                                    rule_params['enabled'] = 0;
                                                }
                                                ajaxCall("/api/anomaly/settings/setRule/"+data['alert_sid'], rule_params, function() {
                                                    $("#alert_sid_action > small").remove();
                                                    $("#alert_sid_action").append($('<small/>').html("{{ lang._('Changes will be active after apply (rules tab)') }}"));
                                                });
                                            });
                                            alert_enabled.change(function(){
                                                alert_select.change();
                                            });
                                        }
                                        if (data['payload_printable'] != undefined && data['payload_printable'] != null) {
                                            tbl_tbody.append(
                                              $("<tr/>").append(
                                                $("<td colspan=2/>").append(
                                                  $("<strong/>").text("{{ lang._('Payload') }}")
                                                )
                                              )
                                            );

                                            var row = $("<tr/>");
                                            row.append( $("<td colspan=2/>").append($("<pre/>").html($("<code/>").text(data['payload_printable']))));
                                            tbl_tbody.append(row);
                                        }

                                        tbl.append(tbl_tbody);
                                        stdDialogInform("{{ lang._('Alert info') }}", tbl, "{{ lang._('Close') }}", undefined, "info", 'suricata-alert');
                                        alert_select.selectpicker('refresh');
                                  });
                                }
                            });
                    }).end();
              });
            } else if (e.target.id == 'userrules_tab') {
                $('#grid-userrules').bootgrid('destroy'); // always destroy previous grid, so data is always fresh
                $("#grid-userrules").UIBootgrid({
                        search:'/api/anomaly/settings/searchUserRule',
                        get:'/api/anomaly/settings/getUserRule/',
                        set:'/api/anomaly/settings/setUserRule/',
                        add:'/api/anomaly/settings/addUserRule/',
                        del:'/api/anomaly/settings/delUserRule/',
                        toggle:'/api/anomaly/settings/toggleUserRule/'
                    }
                );
            }
        });



        /*************************************************************************************************************
         * UI button Commands
         *************************************************************************************************************/

        /**
         * save settings and reconfigure anomaly
         */
        $("#reconfigureTestingAct").SimpleActionButton({
            onPreAction: function() {
                const dfObj = new $.Deferred();
                saveFormToEndpoint("/api/anomaly/labeling-settings/set", 'frm_LabelingSettings', function(){
                    dfObj.resolve();
                });
                return dfObj;
            }
        });
        $("#reconfigureInferringAct").SimpleActionButton({
            onPreAction: function() {
                const dfObj = new $.Deferred();
                saveFormToEndpoint("/api/anomaly/inferring-settings/set", 'frm_InferringSettings', function(){
                    dfObj.resolve();
                });
                return dfObj;
            }
        });
        $("#reconfigureAct").SimpleActionButton({
            onPreAction: function() {
                const dfObj = new $.Deferred();
                saveFormToEndpoint("/api/anomaly/settings/set", 'frm_GeneralSettings', function(){
                    dfObj.resolve();
                });
                return dfObj;
            }
        });
        $("#reconfigureDataProcessorAct").SimpleActionButton({
            onPreAction: function() {
                const dfObj = new $.Deferred();
                saveFormToEndpoint("/api/anomaly/data-processor-settings/set", 'frm_DataProcessorSettings', function(){
                    dfObj.resolve();
                });
                return dfObj;
            }
        });
        $("#updateSettings").click(function(){
            $("#updateSettings_progress").addClass("fa fa-spinner fa-pulse");
            var settings = {};
            $(".rulesetprop").each(function(){
                settings[$(this).data('id')] = $(this).val();
            });
            ajaxCall("/api/anomaly/settings/setRulesetproperties", {'properties': settings}, function(data,status) {
                $("#updateSettings_progress").removeClass("fa fa-spinner fa-pulse");
                $("#rulesetChangeMessage").slideDown(1000, function(){
                    setTimeout(function(){
                        $("#rulesetChangeMessage").slideUp(2000);
                    }, 2000);
                });
            });
        });

        /**
         * update (userdefined) rules
         */
        $(".act_update").SimpleActionButton();

        /**
         * update rule definitions
         */
        $("#updateRulesAct").SimpleActionButton({
            onAction: function(){
                $('#grid-rule-files').bootgrid('reload');
            }
        });

        /**
         * link query alerts button.
         */
        $("#actQueryAlerts").click(function(){
            $('#grid-alerts').bootgrid('reload');
        });
        $("#inputSearchAlerts").keypress(function (e) {
            if (e.which == 13) {
                $("#actQueryAlerts").click();
            }
        });

        $("#grid-rule-files-search").keydown(function (e) {
            var searchString = $(this).val();
            $("#grid-rule-files > tbody > tr").each(function(){
                var itemName = $(this).children('td:eq(1)').html();
                if (itemName.toLowerCase().indexOf(searchString.toLowerCase())>=0) {
                    $(this).show();
                } else {
                    $(this).hide();
                }
            });
        });

        /**
         * Initialize
         */
        // fetch interface mappings on load
        ajaxGet('/api/diagnostics/interface/getInterfaceNames', {}, function(data, status) {
            interface_descriptions = data;
        });

        updateStatus();

        // update history on tab state and implement navigation
        if (window.location.hash != "") {
            $('a[href="' + window.location.hash + '"]').click();
        } else {
            $('a[href="#settings"]').click();
        }

        $('.nav-tabs a').on('shown.bs.tab', function (e) {
            history.pushState(null, null, e.target.hash);
        });

        // delete selected alert log
        $("#actDeleteLog").click(function(){
            var selected_log = $("#alert-logfile > option:selected");
            BootstrapDialog.show({
                type:BootstrapDialog.TYPE_DANGER,
                title: '{{ lang._('Remove log file ') }} ' + selected_log.html(),
                message: '{{ lang._('Removing this file will cleanup disk space, but cannot be undone.') }}',
                buttons: [{
                    icon: 'fa fa-trash-o',
                    label: '{{ lang._('Yes') }}',
                    cssClass: 'btn-primary',
                    action: function(dlg){
                        ajaxCall("/api/anomaly/service/dropAlertLog/", {filename: selected_log.data('filename')}, function(data,status){
                            updateAlertLogs();
                        });
                        dlg.close();
                    }
                }, {
                    label: '{{ lang._('Close') }}',
                    action: function(dlg){
                        dlg.close();
                    }
                }]
            });

        });

        $("#regenerate_cache_dataprocessor").click(function(){
            $("#regenerate_cache_dataprocessor_progress").addClass("fa fa-spinner fa-pulse");
            ajaxCall("/api/anomaly/data-processor-settings/regeneratelocaldatasets", {'cleanCache': 1}, function(data,status) {
                $("#regenerate_cache_dataprocessor_progress").removeClass("fa fa-spinner fa-pulse");
                if (status != "success" || data['status'] != 'ok' ) {
                    // fix error handling
                    BootstrapDialog.show({
                        type:BootstrapDialog.TYPE_WARNING,
                        title: 'Regenerate cache fail',
                        message: JSON.stringify(data),
                        draggable: true
                    });
                }
            });
        });

        $("#scan_new_cache_dataprocessor").click(function(){
            $("#scan_new_cache_dataprocessor_progress").addClass("fa fa-spinner fa-pulse");
            ajaxCall("/api/anomaly/data-processor-settings/regeneratelocaldatasets", {'cleanCache': 0}, function(data,status) {
                $("#scan_new_cache_dataprocessor_progress").removeClass("fa fa-spinner fa-pulse");
                if (status != "success" || data['status'] != 'ok' ) {
                    // fix error handling
                    BootstrapDialog.show({
                        type:BootstrapDialog.TYPE_WARNING,
                        title: 'Regenerate cache fail',
                        message: JSON.stringify(data),
                        draggable: true
                    });
                }
            });
        });
    });

</script>

<ul class="nav nav-tabs" data-tabs="tabs" id="maintabs">
    <li><a data-toggle="tab" href="#labelingSettings" id="labelingSettings_tab">{{ lang._('1.Labeling data') }}</a></li>
    <li><a data-toggle="tab" href="#dataProcessorSettings" id="dataProcessorSettings_tab">{{ lang._('2.Normalize data') }}</a></li>
    <li><a data-toggle="tab" href="#settings" id="settings_tab">{{ lang._('3.Training AI Model') }}</a></li>
    <li><a data-toggle="tab" href="#inferringSettings" id="inferringSettings_tab">{{ lang._('4.Inferring traffic') }}</a></li>
    <li><a data-toggle="tab" href="#training_histories" id="training_histories_tab">{{ lang._('5.Extracted rules') }}</a></li>
</ul>
<div class="tab-content content-box">
    <div id="labelingSettings" class="tab-pane fade in">
        {{ partial("layout_partials/base_form",['fields':formLabelingSettings,'id':'frm_LabelingSettings'])}}
        <div class="col-md-12">
            <hr/>
            <button class="btn btn-primary" id="reconfigureTestingAct"
                    data-endpoint='/api/anomaly/labeling-service/reconfigure'
                    data-label="{{ lang._('Start labeling') }}"
                    data-error-title="{{ lang._('Error reconfiguring Anomaly') }}"
                    data-service-widget="anomaly"
                    type="button"
            ></button>
            &nbsp;&nbsp;<span id="scheduled_updates_labeling" class="btn btn-primary" style="display:none"><a href="" style="color: #fff">{{ lang._('Schedule') }}</a></span>
            <br/>
            <br/>
        </div>
        {# { partial("layout_partials/dataset_form",['fields':formLabelingSettings,'id':'frm_LabelingSettings_Dataset','api':'/api/anomaly/labeling-settings/'])} #}
    </div>
    <div id="inferringSettings" class="tab-pane fade in">
        {{ partial("layout_partials/base_form",['fields':formInferringSettings,'id':'frm_InferringSettings'])}}
        <div class="col-md-12">
            <hr/>
            <button class="btn btn-primary" id="reconfigureInferringAct"
                    data-endpoint='/api/anomaly/inferring-service/reconfigure'
                    data-label="{{ lang._('Start inferring') }}"
                    data-error-title="{{ lang._('Error reconfiguring Anomaly') }}"
                    data-service-widget="anomaly"
                    type="button"
            ></button>
            &nbsp;&nbsp;<span id="scheduled_updates_inferring" class="btn btn-primary" style="display:none"><a href="" style="color: #fff">{{ lang._('Schedule') }}</a></span>
            <br/>
            <br/>
        </div>
        {# { partial("layout_partials/dataset_form",['fields':formInferringSettings,'id':'frm_InferringSettings_Dataset','api':'/api/anomaly/inferring-settings/'])} #}
    </div>
    <div id="settings" class="tab-pane fade in">
        {{ partial("layout_partials/base_form",['fields':formGeneralSettings,'id':'frm_GeneralSettings'])}}
        <div class="col-md-12">
            <hr/>
            <button class="btn btn-primary" id="reconfigureAct"
                    data-endpoint='/api/anomaly/service/reconfigure'
                    data-label="{{ lang._('Train') }}"
                    data-error-title="{{ lang._('Error reconfiguring Anomaly') }}"
                    data-service-widget="anomaly"
                    type="button"
            ></button>
            &nbsp;&nbsp;<span id="scheduled_updates_general" class="btn btn-primary" style="display:none"><a href="" style="color: #fff">{{ lang._('Schedule') }}</a></span>
            <br/>
            <br/>
        </div>
        {# { partial("layout_partials/dataset_form",['fields':formGeneralSettings,'id':'frm_GeneralSettings_Dataset','api':'/api/anomaly/settings/'])} #}
    </div>
    <div id="dataProcessorSettings" class="tab-pane fade in">
        {{ partial("layout_partials/base_form",['fields':formDataProcessorSettings,'id':'frm_DataProcessorSettings'])}}
        <div class="col-md-12">
            <hr/>
            <button class="btn btn-primary" id="reconfigureDataProcessorAct"
                    data-endpoint='/api/anomaly/data-processor-service/reconfigure'
                    data-label="{{ lang._('Process') }}"
                    data-error-title="{{ lang._('Error reconfiguring Anomaly Data Processor') }}"
                    data-service-widget="anomaly"
                    type="button"
            ></button>
            &nbsp;&nbsp;<span id="scheduled_updates_dataprocessor" class="btn btn-primary" style="display:none"><a href="" style="color: #fff">{{ lang._('Schedule') }}</a></span>
            &nbsp;&nbsp;<span id="scheduled_updates_dataprocessorcic" class="btn btn-primary" style="display:none"><a href="" style="color: #fff">{{ lang._('Schedule CIC') }}</a></span>
            &nbsp;&nbsp;<button class="btn btn-primary" id="regenerate_cache_dataprocessor" type="button">{{ lang._('Regenerate cache') }}<i id="regenerate_cache_dataprocessor_progress" class=""></i></button>
            &nbsp;&nbsp;<button class="btn btn-primary" id="scan_new_cache_dataprocessor" type="button">{{ lang._('Scan new cache') }}<i id="scan_new_cache_dataprocessor_progress" class=""></i></button>
            <br/>
            <br/>
        </div>
        {# { partial("layout_partials/dataset_form",['fields':formDataProcessorSettings,'id':'frm_DataProcessorSettings_Dataset','api':'/api/anomaly/data-processor-settings/'])} #}
    </div>
    <div id="training_histories" class="tab-pane fade in">
      <!-- add installable rule files -->
      <table class="table table-striped table-condensed table-responsive">
          <tbody>
            <tr>
                <td><div class="control-label">
                    <i class="fa fa-info-circle text-muted"></i>
                    <b>{{ lang._('Rulesets') }}</b>
                    </div>
                </td>
                <td>
                  <table class="table table-condensed table-responsive">
                    <tr>
                      <td>
                        <div class="row">
                          <div class="col-xs-9">
                            <div>
                              <button data-toggle="tooltip" id="enableSelectedRuleSets" type="button" class="btn btn-xs btn-default btn-primary">
                                  {{ lang._('Enable selected') }}
                              </button>
                              <button data-toggle="tooltip" id="enabledropSelectedRuleSets" type="button" class="btn btn-xs btn-default btn-primary">
                                  {{ lang._('Enable (drop filter)') }}
                              </button>
                              <button data-toggle="tooltip" id="enableclearSelectedRuleSets" type="button" class="btn btn-xs btn-default btn-primary">
                                  {{ lang._('Enable (clear filter)') }}
                              </button>
                              <button data-toggle="tooltip" id="disableSelectedRuleSets" type="button" class="btn btn-xs btn-default btn-primary">
                                  {{ lang._('Disable selected') }}
                              </button>
                            </div>
                          </div>
                          <div class="col-xs-3" style="padding-top:0px;">
                            <input type="text" placeholder="{{ lang._('Search') }}" id="grid-rule-files-search" value=""/>
                          </div>
                        </div>
                      </td>
                    </tr>
                  </table>
                  <div style="max-height: 400px; width: 100%; margin: 0; overflow-y: auto;" id="grid-rule-files-container">
                    <table id="grid-rule-files" class="table table-condensed table-hover table-striped table-responsive" data-editAlert="rulesetChangeMessage" data-editDialog="DialogRuleset">
                        <thead>
                        <tr>
                            <th data-column-id="filename" data-type="string" data-visible="false" data-identifier="true">{{ lang._('Filename') }}</th>
                            <th data-column-id="description" data-type="string" data-sortable="false" data-visible="true">{{ lang._('Description') }}</th>
                            <th data-column-id="modified_local" data-type="rulets" data-sortable="false" data-visible="true">{{ lang._('Last updated') }}</th>
                            <th data-column-id="enabled" data-formatter="boolean" data-sortable="false" data-width="10em">{{ lang._('Enabled') }}</th>
                            <th data-column-id="filter_str" data-type="string" data-identifier="true">{{ lang._('Filter') }}</th>
                            <th data-column-id="edit" data-formatter="editor" data-sortable="false" data-width="10em">{{ lang._('Edit') }}</th>
                        </tr>
                        </thead>
                        <tbody>
                        </tbody>
                    </table>
                  </div>
                </td>
            </tr>
            <tr style="display:none">
                <td><div class="control-label">
                    <i class="fa fa-info-circle text-muted"></i>
                    <b>{{ lang._('Settings') }}</b>
                    </div>
                </td>
                <td>
                  <table id="grid-rule-files-settings" class="table-condensed table-hover">
                    <tbody>
                    </tbody>
                  </table>
                </td>
            </tr>
          </tbody>
      </table>
      <div class="col-md-12">
          <div id="rulesetChangeMessage" class="alert alert-info" style="display: none" role="alert">
              {{ lang._('Please use "Download & Update Rules" to fetch your initial ruleset, automatic updating can be scheduled after the first download.') }}
          </div>
          <hr/>
          <button class="btn btn-primary" style="display:none" id="updateSettings" type="button"><b>{{ lang._('Save') }}</b> <i id="updateSettings_progress" class=""></i></button>

          <button class="btn btn-primary" id="updateRulesAct"
                  data-endpoint='/api/anomaly/service/updateRules'
                  data-label="{{ lang._('Download & Update Rules') }}"
                  data-error-title="{{ lang._('Error reconfiguring Anomaly') }}"
                  data-service-widget="anomaly"
                  type="button"
          ></button>
          <br/><br/>
      </div>
    </div>

    {{ partial("layout_partials/dataset_form",['fields':formDataProcessorSettings,'id':'frm_DataProcessorSettings_Dataset','api':'/api/anomaly/data-processor-settings/'])}}
</div>

{{ partial("layout_partials/base_dialog_processing") }}

{{ partial("layout_partials/base_dialog",['fields':formDialogRule,'id':'DialogRule','label':lang._('Rule details'),'hasSaveBtn':'true','msgzone_width':1])}}
{{ partial("layout_partials/base_dialog",['fields':formDialogRuleset,'id':'DialogRuleset','label':lang._('Ruleset details'),'hasSaveBtn':'true','msgzone_width':1])}}
{{ partial("layout_partials/base_dialog",['fields':formDialogUserDefined,'id':'DialogUserDefined','label':lang._('Rule details'),'hasSaveBtn':'true'])}}
