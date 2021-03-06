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
  var show_rule_scores = function(rule_id, test){
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

  var show_rule_meta = function(rule_id){
    $.ajax({
      dataType: "json",
      url: "/rule/status/" + rule_id,
      success: function(data){
        $('#score-meta').html('');
        $('#score-meta').append('<p><strong>Total Scores:</strong> ' + data.score.score__sum + '</p>')
        $('#score-meta').append('<p><strong>Lines:</strong> ' + data.count + '</p>')
        $.each(data.channels, function(key, channel){
          $('#score-meta').append('<p><strong>' + channel.channel_title + ':</strong> ' + channel.date_scored + ' ' + channel.lines_scored + '/' + channel.line_total + ' lines scored');
          if (channel.locked) {
            $('#score-meta').append('<div class="progress"><div class="bar" style="width: '+ channel.percent_complete + '%;"></div></div>');
          }
        });
      }
    });
  }

  var plot_scores = function(rule_id){
    $.ajax({
      dataType: "json",
      url: "/rule/plot/" + rule_id,
      success: function(data){
        var options = {
          xaxis: {
            mode: "time",
            tickLength: 1,
            timeformat: "%m/%d/%Y",
            minTickSize: [1, "day"]
            // autoscaleMargin: .01
          },
          grid: {
            // hoverable: true,
            // clickable: true,
          },
          series: {
            bars: {
              show: true,
              barWidth : 60*60*21*1000,
              align: 'center'
            },
          },
          selection: {
            mode: "x"
          },
        };
        var plot = $.plot("#score-plot", [data[0].plot_values], options);
        var overview = $.plot("#score-plot-nav", [data[0].plot_values], {
          series: {
            // lines: {
            //   show: true,
            //   lineWidth: 1
            // },
            bars: {
              show: true,
              barWidth : 60*60*21*1000,
              align: 'center'
            },
            shadowSize: 2
          },
          bars: { show: true },
          xaxis: {
            ticks: [],
            mode: "time",
            min: data[0].start_date,
            max: data[0].end_date,
            // autoscaleMargin: 5
          },
          yaxis: {
            ticks: [],
            min: 0,
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
              max: ranges.xaxis.to,
              autoscaleMargin: .1
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
    var rule_id = $("#rule-meta").data('rule-id');
    show_rule_scores(rule_id);
    show_rule_meta(rule_id);
    // This needs to plot by channel too
    plot_scores(rule_id);
    setInterval(function () {
      show_rule_meta(rule_id);
    }, 5000);
  });
})(jQuery);