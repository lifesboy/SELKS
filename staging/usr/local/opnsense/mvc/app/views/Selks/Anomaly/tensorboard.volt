<style>
    #ref-frame {
        position: absolute;
        top: 50px;
        left: 0;
    }
</style>
<script>
$( document ).ready(function() {
    $('#ref-frame').detach().appendTo($('.page-content'))
});
</script>
<iframe id="ref-frame" src="https://selks.ddns.net:444/tensorboard/" title="TensorBoard"
    width="100%" height="100%"
    frameborder="0" allowfullscreen></iframe>