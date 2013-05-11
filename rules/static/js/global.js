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
    if(typeof test !== 'undefined'){
      url = "/rule/scores/test/" + rule_id;
    }
    else{
      url = "/rule/scores/" + rule_id;
    }
    $.ajax({
      dataType: "json",
      url: url,
      success: function(data){
        var items = [];
        $.each(data, function(key, value){
          line = highlightMatches(value);
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
        console.log(data[0]);
        $('#score-meta').html('');
        $.each(data[0], function(key, value){
          $('#score-meta').append('<p><strong>' + key + ':</strong> ' + value + '</p>');
        });
      }
    });
  }

  var plot_scores = function(){
    var rule_id = $("#rule-scores").data('rule-id');
    $.ajax({
      dataType: "json",
      url: "/rule/plot/" + rule_id,
      success: function(data){
        var options = {
          xaxis: {
            mode: "time",
            tickLength: 5
          },
          selection: {
            mode: "x"
          },
        };
        var plot = $.plot("#score-plot", [data[0].plot_values], options);
        var overview = $.plot("#score-plot-nav", [data[0].plot_values], {
          series: {
            lines: {
              show: true,
              lineWidth: 1
            },
            shadowSize: 0
          },
          xaxis: {
            ticks: [],
            mode: "time",
            min: data[0].start_date,
            max: data[0].end_date,
          },
          yaxis: {
            ticks: [],
            min: 0,
            autoscaleMargin: 0.1
          },
          selection: {
            mode: "x"
          }
        });
        $("#score-plot").bind("plotselected", function (event, ranges) {

          // do the zooming

          plot = $.plot("#score-plot", [data[0].plot_values], $.extend(true, {}, options, {
            xaxis: {
              min: ranges.xaxis.from,
              max: ranges.xaxis.to
            }
          }));

          // don't fire event on the overview to prevent eternal loop

          overview.setSelection(ranges, true);
        });
        $("#score-plot-nav").bind("plotselected", function (event, ranges) {
          plot.setSelection(ranges);
        });
      }
    });
  }

  $(document).ready(function(e) {
    show_rule_scores();
    show_rule_meta();
    plot_scores();
    setInterval(function () {
      show_rule_meta();
    }, 5000);
  });
})(jQuery);