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
<form id="{{base_form_id}}" class="form-inline" data-title="{{data_title|default('')}}">
    <div id="rules" class="tab-pane fade in">
        <div class="bootgrid-header container-fluid">
            <div class="row">
                <div class="col-sm-12 actionBar">
                    <select id="rulemetadata" title="{{ lang._('Filters') }}" class="selectpicker" multiple=multiple data-live-search="true" data-size="10" data-width="100%">
                    </select>
                </div>
            </div>
        </div>

        <!-- tab page "installed rules" -->
        <table id="grid-installedrules" data-store-selection="true" class="table table-condensed table-hover table-striped table-responsive" data-editAlert="ruleChangeMessage" data-editDialog="DialogRule">
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
