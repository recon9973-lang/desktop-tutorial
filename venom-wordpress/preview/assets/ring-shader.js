/* 골든 링 — WebGL 조각 셰이더. 영상이 아니라 「시간」을 넣으면 그 순간을 계산해 낸다.
   끝나는 지점이 없으므로 되감기도 없다. 라이브러리 없음.

   원리(원본 영상과 같다): 닫힌 고리를 따라 납작한 띠가 꼬여 돈다. 띠 위의 가닥 N개까지의
   거리를 픽셀마다 재서 1/거리로 빛을 더한다. 가닥이 몰리는 자리가 저절로 타오른다.
   밝기는 ① 앞뒤 깊이 ② 한 방향에서 오는 빛 — 원본을 재보니 밝기의 1차 성분이 97%였다
   (빛이 한쪽에서 온다). 그 밝은 쪽은 돌지 않고 앞뒤로 흔들린다(한 바퀴 순 회전 -2°). */
(function (global) {
  'use strict';

  var VS = 'attribute vec2 p;void main(){gl_Position=vec4(p,0.,1.);}';

  var FS = [
'precision highp float;',
'uniform vec2  res;',
'uniform float t;',
'uniform float strands;',
'uniform vec3  tint;',
'',
'#define PI 6.2831853',
'',
'void main(){',
'  vec2 p = (gl_FragCoord.xy - 0.5*res) / min(res.x,res.y);   // 중심 기준, -0.5~0.5',
'  float ct = cos(0.30), st = sin(0.30);                      // 살짝 기울여 입체가 보이게',
'  vec2  q  = vec2(p.x, p.y/ct);                              // 기울기를 되돌린 자리',
'  float r  = length(q);',
'  float a  = atan(q.y, q.x);',
'',
'  // 모양을 천천히 바꾸는 위상 — 서로 안 맞아떨어지는 속도라 같은 그림이 반복되지 않는다',
'  float p1 = t*0.17, p2 = -t*0.11, p3 = t*0.21, p4 = t*0.33;',
'  float lobe = 1.0 + 0.090*sin(3.0*a + p1) + 0.052*sin(2.0*a + p2);',
'  float W    = 0.055*(1.0 + 0.34*sin(2.0*a + p3));           // 띠 너비가 자리마다 다르다',
'  float tw   = 2.0*a + p4;                                   // 띠가 꼬이는 각',
'',
'  // 빛은 한 방향에서 온다. 그 방향은 돌지 않고 흔들린다.',
'  float LA   = 2.6 + 0.9*sin(t*0.23);',
'  float side = 0.30 + 0.70*(0.5 + 0.5*cos(a - LA));',
'',
'  float glow = 0.0;',
'  for (int i = 0; i < 96; i++) {',
'    if (float(i) >= strands) break;',
'    float u = float(i)/(strands-1.0)*2.0 - 1.0;              // 띠 안에서의 자리 -1~+1',
'    float rad = 0.335*lobe + u*W*cos(tw);',
'    float z   = u*W*sin(tw)*1.6;',
'    float Rq  = rad - z*(st/ct)*sin(a);                      // 기울기 때문에 생기는 위아래 밀림',
'    float d   = abs(r - Rq);',
'    float dep = 0.5 + 0.5*(z/(W*1.6+1e-5));                  // 앞(1) ~ 뒤(0)',
'    float w   = (0.35 + 0.65*dep) * side;',
'    float d2 = d*d;',
'    glow += w * (0.0000255/(d2 + 0.00000055)             // 가는 심 — 가닥 하나하나가 보인다',
'               + 0.000204/(d2 + 0.00026));               // 넓은 번짐 — 링을 감싸는 헤일로',
'  }',
'  glow /= strands;',
'',
'  float v = glow;',
'  vec3  c = tint * v;',
'  c += vec3(1.0,0.80,0.58) * pow(max(v-1.45,0.0), 1.7) * 0.20;  // 진짜 핵만 흰빛',
'  float al = clamp(max(max(c.r,c.g),c.b), 0.0, 1.0);',
'  gl_FragColor = vec4(min(c,vec3(1.0)), al);',
'}'].join('\n');

  function compile(gl, type, src) {
    var s = gl.createShader(type);
    gl.shaderSource(s, src); gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
    return s;
  }

  function make(canvas, opt) {
    opt = opt || {};
    var gl = canvas.getContext('webgl', { alpha: true, premultipliedAlpha: false, antialias: false });
    if (!gl) return null;
    var pr = gl.createProgram();
    gl.attachShader(pr, compile(gl, gl.VERTEX_SHADER, VS));
    gl.attachShader(pr, compile(gl, gl.FRAGMENT_SHADER, FS));
    gl.linkProgram(pr);
    if (!gl.getProgramParameter(pr, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(pr));
    gl.useProgram(pr);
    var buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1, 3,-1, -1,3]), gl.STATIC_DRAW);
    var loc = gl.getAttribLocation(pr, 'p');
    gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
    var uRes = gl.getUniformLocation(pr, 'res'),
        uT   = gl.getUniformLocation(pr, 't'),
        uN   = gl.getUniformLocation(pr, 'strands'),
        uC   = gl.getUniformLocation(pr, 'tint');
    var N = opt.strands || 88;
    var tint = opt.tint || [1.0, 0.485, 0.205];     // 원본 밝은 픽셀 평균 R202 G136 B66 의 비율
    var raf = 0, live = false, t0 = 0, S = 0;

    function size() {
      var r = canvas.getBoundingClientRect();
      var dpr = Math.min(global.devicePixelRatio || 1, 2);
      var n = Math.max(32, Math.round((r.width || 220) * dpr));
      if (n !== S) { S = n; canvas.width = canvas.height = S; }
      gl.viewport(0, 0, S, S);
    }
    function frame(ms) {
      if (!live) return;
      if (!t0) t0 = ms;
      size();
      gl.uniform2f(uRes, S, S);
      gl.uniform1f(uT, (ms - t0) / 1000);
      gl.uniform1f(uN, N);
      gl.uniform3f(uC, tint[0], tint[1], tint[2]);
      gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
      raf = global.requestAnimationFrame(frame);
    }
    return {
      start: function(){ if (live) return; live = true; raf = global.requestAnimationFrame(frame); },
      stop:  function(){ live = false; if (raf) global.cancelAnimationFrame(raf); raf = 0; }
    };
  }
  global.RingShader = { make: make };
})(window);
