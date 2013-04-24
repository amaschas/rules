function escapeHtml(unsafe) {
  return unsafe
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
 }

 function highlightMatches(rule){
  // This is a bit clunky, might be a better way
  regex = new RegExp('(' + rule.rule + ')', 'g');
  line = escapeHtml(rule.line.replace(regex, "<span class='highlight'>$1</span>"));
  line = line.replace(/&lt;span class=&#039;highlight&#039;&gt;/g, "<span class='highlight'>");
  line = line.replace(/&lt;\/span&gt;/g, "</span>");
  return line;
 }

(function($) {

  var show_rule_scores = function(test){
    var rule_id = $("#rule-scores").data('rule-id');
    var url = ''
    // console.log(typeof test);
    if(typeof test !== 'undefined'){
      url = "/rule/scores/test/" + rule_id;
    }
    else{
      url = "/rule/scores/" + rule_id;
    }
    // console.log(url);
    $.ajax({
      dataType: "json",
      url: url,
      success: function(data){
        var items = [];
        $.each(data, function(key, value){
          line = highlightMatches(value);
          // console.log(line);
          $('#rule-scores').append('<li>' + line + '</li>');
        });
      }
    });
  }

  var show_rule_meta = function(){
    var rule_id = $("#rule-scores").data('rule-id');
    $.ajax({
      dataType: "json",
      url: "/rule/status/" + rule_id,
      success: function(data){
        console.log(data);
        // var items = [];
        // $.each(data, function(key, value){
        //   line = highlightMatches(value);
        //   // console.log(line);
        //   $('#rule-scores').append('<li>' + line + '</li>');
        // });
      }
    });
  }

  $(document).ready(function(e) {
    show_rule_scores();
    show_rule_meta();
  });
})(jQuery);