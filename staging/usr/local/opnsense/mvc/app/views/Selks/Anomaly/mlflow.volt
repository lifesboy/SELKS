<style>
    #ref-frame {
        position: absolute;
        top: 50px;
        left: 0;
        z-index: 99;
    }
</style>
<script>
$( document ).ready(function() {
    $('#ref-frame').detach().appendTo($('.page-content'))
});
</script>
<iframe id="ref-frame" src="/proxy/mlflow/" title="ML Flow"
    width="100%" height="100%"
    frameborder="0" allowfullscreen></iframe>