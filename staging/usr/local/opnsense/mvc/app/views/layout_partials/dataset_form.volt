{#
 # Copyright (c) 2014-2015 Deciso B.V.
 # All rights reserved.
 #
 # Redistribution and use in source and binary forms, with or without modification,
 # are permitted provided that the following conditions are met:
 #
 # 1. Redistributions of source code must retain the above copyright notice,
 #    this list of conditions and the following disclaimer.
 #
 # 2. Redistributions in binary form must reproduce the above copyright notice,
 #    this list of conditions and the following disclaimer in the documentation
 #    and/or other materials provided with the distribution.
 #
 # THIS SOFTWARE IS PROVIDED "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
 # INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY
 # AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
 # AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
 # OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 # SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 # INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
 # CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 # ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 # POSSIBILITY OF SUCH DAMAGE.
 #}

{#
 # Generate input dialog, uses the following parameters (as associative array):
 #
 # fields          :   list of field type objects, see form_input_tr tag for details
 # id              :   form id, used as unique id for this form.
 # apply_btn_id    :   id to use for apply button (leave empty to ignore)
 # data_title      :   data-title to set on form
 #}

{# Find if there are help supported or advanced field on this page #}
{% set base_form_id=id %}
{% set base_api_endpoint=api %}
{% set help=false %}
{% set advanced=false %}
{% for field in fields|default({})%}
{%     for name,element in field %}
{%         if name=='help' %}
{%             set help=true %}
{%         endif %}
{%         if name=='advanced' %}
{%             set advanced=true %}
{%         endif %}
{%     endfor %}
{%     if help|default(false) and advanced|default(false) %}
{%         break %}
{%     endif %}
{% endfor %}

<script>
    $( document ).ready(function() {
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
                            console.log('call_url', call_url);
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

        /**
         * list all known classtypes and add to selection box
         */
        function updateDatasetMetadata() {
            ajaxGet("{{base_api_endpoint}}listDatasetMetadata", {}, function(data, status) {
                if (status == "success") {
                    $('#{{base_form_id}} #datasetmetadata').empty();
                    $.each(Object.assign({}, {'action': ['drop', 'alert', '']}, data), function(key, values) {
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
                        $('#{{base_form_id}} #datasetmetadata').append($optgroup);
                    });
                    $('#{{base_form_id}} .selectpicker').selectpicker('refresh');
                    // link on change event
                    $('#{{base_form_id}} #datasetmetadata').on('change', function(){
                        $('#{{base_form_id}} #{{base_form_id}}-grid-datasets').bootgrid('reload');
                    });
                }
            });
        }

        /**
         * Add classtype / action to rule filter
         */
        function addRuleFilters(request) {
            // add loading overlay
            $('#processing-dialog').modal('show');
            $("#{{base_form_id}} #{{base_form_id}}-grid-datasets").bootgrid().on("loaded.rs.jquery.bootgrid", function (e){
                $('#processing-dialog').modal('hide');
            });

            $('#{{base_form_id}} #datasetmetadata').find("option:selected").each(function(){
                let filter_name = $(this).data('property');
                if (request[filter_name] === undefined) {
                    request[filter_name] = $(this).data('value');
                } else {
                    request[filter_name] += "," + $(this).data('value');
                }
            });
            return request;
        }

        function validateResponseData(response) {
            $('#{{base_form_id}}').removeClass("has-error");
            $('#{{base_form_id}} .error-message').hide();

            if (response && response.error) {
                var errorMessage = 'Error while loading data: ' + (response.error.msg || 'Unknown')
                $('#{{base_form_id}}').addClass("has-error");
                $('#{{base_form_id}} .error-message').text(errorMessage);
                $('#{{base_form_id}} .error-message').show();
                //alert(errorMessage);
                response.rows = response.rows || [];
                response.total = response.total || 0;
                response.rowCount = response.rowCount || 0;
                response.current = response.current || 0;
                //response.parameters = response.parameters || {};
            }

            return response;
        }

        //
        // activate rule tab page
        //

        // delay refresh for a bit
        setTimeout(updateDatasetMetadata, 500);

        /**
         * grid installed datasets
         */
        $('#{{base_form_id}} #{{base_form_id}}-grid-datasets').bootgrid('destroy'); // always destroy previous grid, so data is always fresh
        $("#{{base_form_id}} #{{base_form_id}}-grid-datasets").UIBootgrid(
            {   search:'{{base_api_endpoint}}searchlocaldatasets',
                get:'{{base_api_endpoint}}getDatasetInfo/',
                set:'{{base_api_endpoint}}setRule/',
                options:{
                    requestHandler:addRuleFilters,
                    responseHandler:validateResponseData,
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
                toggle:'{{base_api_endpoint}}toggleDataset/'
            }
        );
        /**
         * disable/enable [+action] selected datasets
         */
        $("#{{base_form_id}} #disableSelectedRules").unbind('click').click(function(event){
            event.preventDefault();
            $("#{{base_form_id}} #disableSelectedRules > span").removeClass("fa-square-o").addClass("fa-spinner fa-pulse");
            actionToggleSelected('{{base_form_id}}-grid-datasets', '{{base_api_endpoint}}toggleRule/', 0, 100).done(function(){
                $("#disableSelectedRules > span").removeClass("fa-spinner fa-pulse");
                $("#disableSelectedRules > span").addClass("fa-square-o");
            });
        });
        $("#{{base_form_id}} #enableSelectedRules").unbind('click').click(function(){
            $("#{{base_form_id}} #enableSelectedRules > span").removeClass("fa-check-square-o").addClass("fa-spinner fa-pulse");
            actionToggleSelected('{{base_form_id}}-grid-datasets', '{{base_api_endpoint}}toggleRule/', 1, 100).done(function(){
                $("#{{base_form_id}} #enableSelectedRules > span").removeClass("fa-spinner fa-pulse").addClass("fa-check-square-o");
            });
        });
        $("#{{base_form_id}} #alertSelectedRules").unbind('click').click(function(){
            $("#{{base_form_id}} #alertSelectedRules > span").addClass("fa-spinner fa-pulse");
            actionToggleSelected('{{base_form_id}}-grid-datasets', '{{base_api_endpoint}}toggleRule/', "alert", 100).done(function(){
                $("#{{base_form_id}} #alertSelectedRules > span").removeClass("fa-spinner fa-pulse");
            });
        });
        $("#{{base_form_id}} #dropSelectedRules").unbind('click').click(function(){
            $("#{{base_form_id}} #dropSelectedRules > span").addClass("fa-spinner fa-pulse");
            actionToggleSelected('{{base_form_id}}-grid-datasets', '{{base_api_endpoint}}toggleRule/', "drop", 100).done(function(){
                $("#{{base_form_id}} #dropSelectedRules > span").removeClass("fa-spinner fa-pulse");
            });
        });

    });
</script>

<form id="{{base_form_id}}" class="form-inline" data-title="{{data_title|default('')}}">
    <div>
        <label class="error-message control-label"></label>
    </div>
    <div id="datasets" class="tab-pane fade in">
        <div class="bootgrid-header container-fluid">
            <div class="row">
                <div class="col-sm-12 actionBar">
                    <select id="datasetmetadata" title="{{ lang._('Filters') }}" class="selectpicker" multiple=multiple data-live-search="true" data-size="10" data-width="100%">
                    </select>
                </div>
            </div>
        </div>

        <!-- tab page "installed datasets" -->
        <table id="{{base_form_id}}-grid-datasets" data-store-selection="true" class="table table-condensed table-hover table-striped table-responsive" data-editAlert="ruleChangeMessage" data-editDialog="DialogRule">
            <thead>
            <tr>
                <th data-column-id="sid" data-type="numeric" data-visible="true" data-identifier="true" data-width="6em">{{ lang._('sid') }}</th>
                <th data-column-id="action" data-type="string">{{ lang._('Action') }}</th>
                <th data-column-id="source" data-type="string">{{ lang._('Source') }}</th>
                <th data-column-id="classtype" data-type="string">{{ lang._('ClassType') }}</th>
                <th data-column-id="msg" data-type="string">{{ lang._('Message') }}</th>
                <th data-column-id="enabled" data-formatter="rowtoggle" data-sortable="false" data-width="10em">{{ lang._('Info / Enabled') }}</th>
            </tr>
            </thead>
            <tbody>
            </tbody>
            <tfoot>
            <tr>
                <td>
                    <button title="{{ lang._('Disable selected') }}" id="disableSelectedRules" data-toggle="tooltip" type="button" class="btn btn-xs btn-default"><span class="fa fa-square-o"></span></button>
                    <button title="{{ lang._('Enable selected') }}" id="enableSelectedRules" data-toggle="tooltip" type="button" class="btn btn-xs btn-default"><span class="fa fa-check-square-o"></span></button>
                    <button title="{{ lang._('Alert selected') }}" id="alertSelectedRules" data-toggle="tooltip" type="button" class="btn btn-xs btn-default"><span class="fa"></span>{{ lang._('alert') }}</button>
                    <button title="{{ lang._('Drop selected') }}" id="dropSelectedRules" data-toggle="tooltip" type="button" class="btn btn-xs btn-default"><span class="fa"></span>{{ lang._('drop') }}</button>
                </td>
                <td></td>
            </tr>
            </tfoot>
        </table>
        <div class="col-md-12">
            <div id="ruleChangeMessage" class="alert alert-info" style="display: none" role="alert">
                {{ lang._('After changing settings, please remember to apply them with the button below') }}
            </div>
            <hr/>
            <button class="btn btn-primary act_update"
                    data-endpoint='/api/ids/service/reloadRules'
                    data-label="{{ lang._('Apply') }}"
                    data-error-title="{{ lang._('Error reconfiguring IDS') }}"
                    type="button"
            ></button>
            <br/>
            <br/>
        </div>
    </div>
</form>
