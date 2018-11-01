

document.addEventListener('DOMContentLoaded', function(){
  var v = document.getElementById('vid');
  var canvas = document.getElementById('canvas');
  var context = canvas.getContext('2d');

  v.addEventListener('pause', function(){
    draw(v,context);
  },false);
  v.addEventListener('seeked', function(){
    draw(v,context);
  },false);
  v.addEventListener('play', function(){
    clearCanvas(context);
  },false);
},false);


function clearCanvas(c) {
  c.clearRect(0, 0, canvas.width, canvas.height);
}

function draw(v,c) {
  // Setup canvas
  clearCanvas(c);
  var cw = v.clientWidth;
  var ch = v.clientHeight;
  canvas.width = cw;
  canvas.height = .9 * ch;

  var frameRate = 23.98 // Hardcoding this for now but could be fetched from db
  var currentTime = v.currentTime;
  var currentFrame = Math.round(currentTime * frameRate);

  $.ajax({
    url: `/detections/${videoId}/${currentFrame}`,
    dataType: "json",
    success: function( data ){
      $.each(data, function(ix, d){
        var cornerX = d["x_min"] * cw;
        var cornerY = d["y_min"] * ch;
        var width = (d["x_max"] - d["x_min"]) * cw;
        var height = (d["y_max"] - d["y_min"]) * ch;

        c.beginPath();
        c.lineWidth="4";
        c.strokeStyle="white";
        c.rect(cornerX, cornerY, width, height);
        c.stroke();
        c.font = "14px Arial";
        c.fillStyle = "white";
        c.fillText(`${d["object_name"]}: ${d["score"]}`, cornerX+6, cornerY+18);
      });
    }
  });
}
