

<tr id="row_<?= $id ?>" <?php if ((empty($advanced) ? (false) : ($advanced)) == 'true') { ?> data-advanced="true"<?php } ?>>
    <td>
        <div class="control-label" id="control_label_<?= $id ?>">
            <?php if ((empty($help) ? (false) : ($help))) { ?>
                <a id="help_for_<?= $id ?>" href="#" class="showhelp"><i class="fa fa-info-circle"></i></a>
            <?php } elseif ((empty($help) ? (false) : ($help)) == false) { ?>
                <i class="fa fa-info-circle text-muted"></i>
            <?php } ?>
            <b><?= $label ?></b>
        </div>
    </td>
    <td>
        <?php if ($type == 'text') { ?>
            <input type="text" class="form-control <?= (empty($style) ? ('') : ($style)) ?>" size="<?= (empty($size) ? ('50') : ($size)) ?>" id="<?= $id ?>" <?= ((empty($readonly) ? (false) : ($readonly)) ? 'readonly="readonly"' : '') ?> >
        <?php } elseif ($type == 'hidden') { ?>
            <input type="hidden" id="<?= $id ?>" class="<?= (empty($style) ? ('') : ($style)) ?>" >
        <?php } elseif ($type == 'checkbox') { ?>
            <input type="checkbox"  class="<?= (empty($style) ? ('') : ($style)) ?>" id="<?= $id ?>">
        <?php } elseif ($type == 'select_multiple') { ?>
            <select multiple="multiple"
                    <?php if ((empty($size) ? (false) : ($size))) { ?>data-size="<?= $size ?>"<?php } ?>
                    id="<?= $id ?>"
                    class="<?= (empty($style) ? ('selectpicker') : ($style)) ?>"
                    <?php if ((empty($hint) ? (false) : ($hint))) { ?>data-hint="<?= $hint ?>"<?php } ?>
                    data-width="<?= (empty($width) ? ('334px') : ($width)) ?>"
                    data-allownew="<?= (empty($allownew) ? ('false') : ($allownew)) ?>"
                    data-sortable="<?= (empty($sortable) ? ('false') : ($sortable)) ?>"
                    data-live-search="true"
                    <?php if ((empty($separator) ? (false) : ($separator))) { ?>data-separator="<?= $separator ?>"<?php } ?>
            ></select><?php if ((empty($style) ? ('selectpicker') : ($style)) != 'tokenize') { ?><br /><?php } ?>
            <a href="#" class="text-danger" id="clear-options_<?= $id ?>"><i class="fa fa-times-circle"></i> <small><?= $lang->_('Clear All') ?></small></a>
        <?php } elseif ($type == 'dropdown') { ?>
            <select data-size="<?= (empty($size) ? (10) : ($size)) ?>" id="<?= $id ?>" class="<?= (empty($style) ? ('selectpicker') : ($style)) ?>" data-width="<?= (empty($width) ? ('334px') : ($width)) ?>"></select>
        <?php } elseif ($type == 'password') { ?>
            <input type="password" class="form-control <?= (empty($style) ? ('') : ($style)) ?>" size="<?= (empty($size) ? ('50') : ($size)) ?>" id="<?= $id ?>" <?= ((empty($readonly) ? (false) : ($readonly)) ? 'readonly="readonly"' : '') ?> >
        <?php } elseif ($type == 'textbox') { ?>
            <textarea class="<?= (empty($style) ? ('') : ($style)) ?>" rows="<?= (empty($height) ? ('5') : ($height)) ?>" id="<?= $id ?>" <?= ((empty($readonly) ? (false) : ($readonly)) ? 'readonly="readonly"' : '') ?>></textarea>
        <?php } elseif ($type == 'info') { ?>
            <span  class="<?= (empty($style) ? ('') : ($style)) ?>" id="<?= $id ?>"></span>
        <?php } ?>
        <?php if ((empty($help) ? (false) : ($help))) { ?>
            <div class="hidden" data-for="help_for_<?= $id ?>">
                <small><?= $help ?></small>
            </div>
        <?php } ?>
    </td>
    <td>
        <span class="help-block" id="help_block_<?= $id ?>"></span>
    </td>
</tr>
