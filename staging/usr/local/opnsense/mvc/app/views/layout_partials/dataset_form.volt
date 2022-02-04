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
         * list all known classtypes and add to selection box
         */
        function updateRuleMetadata() {
            ajaxGet("/api/anomaly/settings/listDatasetMetadata", {}, function(data, status) {
                if (status == "success") {
                    $('#{{base_form_id}} #rulemetadata').empty();
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
                        $('#{{base_form_id}} #rulemetadata').append($optgroup);
                    });
                    $('#{{base_form_id}} .selectpicker').selectpicker('refresh');
                    // link on change event
                    $('#{{base_form_id}} #rulemetadata').on('change', function(){
                        $('#{{base_form_id}} #grid-datasets').bootgrid('reload');
                    });
                }
            });
        }

        /**
         * Add classtype / action to rule filter
         */
        function addRuleFilters(request) {
            $('#{{base_form_id}} #rulemetadata').find("option:selected").each(function(){
                let filter_name = $(this).data('property');
                if (request[filter_name] === undefined) {
                    request[filter_name] = $(this).data('value');
                } else {
                    request[filter_name] += "," + $(this).data('value');
                }
            });
            return request;
        }

        //
        // activate rule tab page
        //

        // delay refresh for a bit
        setTimeout(updateRuleMetadata, 500);

        /**
         * grid installed datasets
         */
        $('#{{base_form_id}} #grid-datasets').bootgrid('destroy'); // always destroy previous grid, so data is always fresh
        $("#{{base_form_id}} #grid-datasets").UIBootgrid(
            {   search:'/api/anomaly/settings/searchlocaldatasets',
                get:'/api/ids/settings/getRuleInfo/',
                set:'/api/ids/settings/setRule/',
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
                toggle:'/api/ids/settings/toggleRule/'
            }
        );
        /**
         * disable/enable [+action] selected datasets
         */
        $("#{{base_form_id}} #disableSelectedRules").unbind('click').click(function(event){
            event.preventDefault();
            $("#{{base_form_id}} #disableSelectedRules > span").removeClass("fa-square-o").addClass("fa-spinner fa-pulse");
            actionToggleSelected('grid-datasets', '/api/ids/settings/toggleRule/', 0, 100).done(function(){
                $("#disableSelectedRules > span").removeClass("fa-spinner fa-pulse");
                $("#disableSelectedRules > span").addClass("fa-square-o");
            });
        });
        $("#{{base_form_id}} #enableSelectedRules").unbind('click').click(function(){
            $("#{{base_form_id}} #enableSelectedRules > span").removeClass("fa-check-square-o").addClass("fa-spinner fa-pulse");
            actionToggleSelected('grid-datasets', '/api/ids/settings/toggleRule/', 1, 100).done(function(){
                $("#{{base_form_id}} #enableSelectedRules > span").removeClass("fa-spinner fa-pulse").addClass("fa-check-square-o");
            });
        });
        $("#{{base_form_id}} #alertSelectedRules").unbind('click').click(function(){
            $("#{{base_form_id}} #alertSelectedRules > span").addClass("fa-spinner fa-pulse");
            actionToggleSelected('grid-datasets', '/api/ids/settings/toggleRule/', "alert", 100).done(function(){
                $("#{{base_form_id}} #alertSelectedRules > span").removeClass("fa-spinner fa-pulse");
            });
        });
        $("#{{base_form_id}} #dropSelectedRules").unbind('click').click(function(){
            $("#{{base_form_id}} #dropSelectedRules > span").addClass("fa-spinner fa-pulse");
            actionToggleSelected('grid-datasets', '/api/ids/settings/toggleRule/', "drop", 100).done(function(){
                $("#{{base_form_id}} #dropSelectedRules > span").removeClass("fa-spinner fa-pulse");
            });
        });

    });
</script>

<form id="{{base_form_id}}" class="form-inline" data-title="{{data_title|default('')}}">
    <div id="datasets" class="tab-pane fade in">
        <div class="bootgrid-header container-fluid">
            <div class="row">
                <div class="col-sm-12 actionBar">
                    <select id="rulemetadata" title="{{ lang._('Filters') }}" class="selectpicker" multiple=multiple data-live-search="true" data-size="10" data-width="100%">
                    </select>
                </div>
            </div>
        </div>

        <!-- tab page "installed datasets" -->
        <table id="grid-datasets" data-store-selection="true" class="table table-condensed table-hover table-striped table-responsive" data-editAlert="ruleChangeMessage" data-editDialog="DialogRule">
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
