function escapeHtml(unsafe) {
  return unsafe
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
 }

(function($) {
  var show_rule_scores = function(){
    var rule_id = $("#rule-scores").data('rule-id');
    console.log(rule_id);
    $.ajax({
      dataType: "json",
      url: "/rule/scores/" + rule_id,
      success: function(data){
        var items = [];
        $.each(data, function(key, value){
          // This is a bit clunky, might be a better way
          rule = new RegExp('(' + value.rule + ')', 'g');
          line = escapeHtml(value.line.replace(rule, "<span class='highlight'>$1</span>"));
          line = line.replace(/&lt;span class=&#039;highlight&#039;&gt;/g, "<span class='highlight'>");
          line = line.replace(/&lt;\/span&gt;/g, "</span>");
          console.log(line);
          $('#rule-scores').append('<li>' + line + '</li>');
        });
      }
    });
  }
  $(document).ready(function(e) {
    show_rule_scores();
  });
})(jQuery);