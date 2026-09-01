#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合成脚本 v1（阶段一：技术探查 + 最小可行改动）
============================================
把母本A(叙事层) + 母本B(交互层·虚拟数据) 合成为单文件可交互展示页。

【本次最小改动范围】只动 2 个 panel：
  1. p-query 查价  → 静态 readonly 输入 + 硬编码行  =>  真交互：输入 SUM 码 → 过滤虚拟数据 → 渲染最低价行
  2. p-trend 趋势  → 硬编码 SVG 折线               =>  真交互：卡派/快船分组切换 → 数据驱动重绘

【脱敏】仓码(真实 Amazon FBA 码) 映射为 SUM1..SUM6；供应商名沿用 demo 虚拟名；单价为虚拟量级(~5-13元/kg)。
【复用】虚拟数据字段结构对齐母本B US_DATA：{w,s,c,wt,p,u,dd,inbound,t_min,t_max}
【约束】只读 demo_package + 母本；不改 internal-showcase / price-query。
"""
import json
import re
import sys
from collections import Counter

A_PATH = "/app/working/workspaces/NXUwKg/media/FreightGo_项目展示页_AIPM投递版_20260831.html"
B_PATH = "/app/working/workspaces/NXUwKg/demo_package/index.html"
OUT_PATH = "/app/working/workspaces/NXUwKg/demo_package/showcase_combined.html"

N = 6  # 暴露的仓库数量 → SUM1..SUM6

def read(p):
    return open(p, encoding="utf-8").read()

def extract_js_array(text, var):
    m = re.search(r"var %s = (\[.*?\]);" % var, text, re.S)
    if not m:
        raise RuntimeError("cannot find var %s" % var)
    return json.loads(m.group(1))

A = read(A_PATH)
B = read(B_PATH)

us = extract_js_array(B, "US_DATA")

# ---- 选暴露仓库：按记录条数取前 N 个（数据最全）----
cnt = Counter(r["w"] for r in us)
wheels = [w for w, _ in cnt.most_common(N)]
# 稳定排序（保证输出可复现），映射 SUM1..SUM_n
wheels_sorted = sorted(wheels)
SUM_MAP = {w: "SUM%d" % (i + 1) for i, w in enumerate(wheels_sorted)}
GEO_TAG = "演示仓"

# ---- 构建脱敏数据集（只保留暴露仓库）----
demo = []
for r in us:
    if r["w"] not in SUM_MAP:
        continue
    demo.append({
        "w": SUM_MAP[r["w"]],
        "s": r["s"],          # 虚拟供应商名（母本B）
        "c": r["c"],
        "wt": r["wt"],
        "p": r["p"],
        "u": r["u"],
        "dd": r["dd"],
        "inbound": r["inbound"],
        "t_min": r["t_min"],
        "t_max": r["t_max"],
    })
demo.sort(key=lambda r: (r["w"], r["c"], r["s"], r["wt"]))
demo_json = json.dumps(demo, ensure_ascii=False, separators=(",", ":"))

# 暴露仓库的 SUM 码 + 展示名
wh_keys = {SUM_MAP[w]: w for w in wheels_sorted}
wh_json = json.dumps(wh_keys, ensure_ascii=False, separators=(",", ":"))

# ---- 1) 替换 p-query 静态块为交互容器 ----
pq_start = A.index("        <!-- 询价查询 -->")
pq_end = A.index("        <!-- 智能比价 -->")
pq_new = '''        <!-- 询价查询（合成：真交互，复用 demo 虚拟数据·脱敏） -->
        <div class="demo-panel on" id="p-query">
          <div class="q-search">
            <input type="text" id="qInput" value="" placeholder="输入仓库代码，如 SUM1 / SUM2 / SUM3" autocomplete="off">
            <button id="qBtn">查价</button>
          </div>
          <div class="q-result-head" id="qHead">
            <span class="q-wh" id="qWh">SUM1 <span class="q-wh-badge">演示仓</span></span>
            <span style="font-size:13px;color:var(--muted)">按最低单价排序 · 每渠道取最低档</span>
          </div>
          <div class="q-head">
            <span>供应商</span><span>渠道</span><span style="text-align:right">单价</span><span style="text-align:right">时效</span><span style="text-align:right">进仓地</span>
          </div>
          <div id="qList"></div>
        </div>

'''
A = A[:pq_start] + pq_new + A[pq_end:]

# ---- 2) 替换 p-trend 静态 legend 为交互分组 ----
# p-trend 块的 legend 部分：加上“卡派系 / 快船系”切换控件
trend_legend_old = '''          <div class="trend-legend">
            <span class="trend-lg"><span class="sw" style="background:#0071e3"></span>普船特惠卡派</span>
            <span class="trend-lg"><span class="sw" style="background:#30b352"></span>普船卡派</span>
            <span class="trend-lg"><span class="sw" style="background:#ff9f0a"></span>美森CLX正班卡派</span>
            <span class="trend-lg"><span class="sw" style="background:#ff3b30"></span>美森MAX加班卡派</span>
          </div>'''
trend_legend_new = '''          <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:18px">
            <span style="font-size:12px;color:var(--sub);font-weight:600;letter-spacing:.05em">趋势分组</span>
            <div class="demo-tab on" data-tgrp="kp" style="font-size:12px;padding:6px 16px">卡派系列</div>
            <div class="demo-tab" data-tgrp="fast" style="font-size:12px;padding:6px 16px">快船系列</div>
          </div>
          <div class="trend-legend" id="trendLegend">
            <span class="trend-lg"><span class="sw" style="background:#0071e3"></span>普船特惠卡派</span>
            <span class="trend-lg"><span class="sw" style="background:#30b352"></span>普船卡派</span>
            <span class="trend-lg"><span class="sw" style="background:#ff9f0a"></span>美森CLX正班卡派</span>
            <span class="trend-lg"><span class="sw" style="background:#ff3b30"></span>美森MAX加班卡派</span>
          </div>'''
if trend_legend_old in A:
    A = A.replace(trend_legend_old, trend_legend_new)
else:
    print("[warn] trend-legend 未匹配，跳过", file=sys.stderr)

# ---- 3) 替换 drawTrend IIFE 为数据驱动版本 ----
dt_start = A.index("(function drawTrend(){")
dt_end = A.index("})();", dt_start) + len("})();")
A = A[:dt_start] + "/* 趋势图由下方注入脚本的数据驱动 drawTrendGrid 渲染 */" + A[dt_end:]

# ---- 4) 注入交互脚本（含脱敏虚拟数据）----
inject_script = """
<script>
/* ===== 合成注入：查价 + 趋势 真交互（复用 demo 虚拟数据 · 仓码→SUM 码脱敏） ===== */
var DEMO_WH_KEYS = %(wh)s;
var DEMO_US = %(us)s;
var DEMO_GEO = "演示仓";

function queryWarehouse(raw){
  var code = (raw||'').trim().toUpperCase();
  var list = document.getElementById('qList');
  var head = document.getElementById('qHead');
  if(!list) return;
  if(!code){
    list.innerHTML = '<div class="q-row" style="justify-content:center;color:var(--muted)">输入仓码开始查价</div>';
    return;
  }
  var meta = null;
  for(var k in DEMO_WH_KEYS){ if(k===code){ meta=k; break; } }
  if(!meta){
    list.innerHTML = '<div class="q-row" style="justify-content:center;color:var(--muted)">未找到该仓码，可试：' +
      Object.keys(DEMO_WH_KEYS).join(' / ') + '</div>';
    return;
  }
  var whEl = document.getElementById('qWh');
  if(whEl) whEl.innerHTML = meta + ' <span class="q-wh-badge">' + DEMO_GEO + '</span>';
  var recs = DEMO_US.filter(function(r){ return r.w === meta; });
  if(!recs.length){
    list.innerHTML = '<div class="q-row" style="justify-content:center;color:var(--muted)">该仓暂无价格数据</div>';
    return;
  }
  // 每个 (供应商,渠道) 取最低价档
  var bestByKey = {};
  recs.forEach(function(r){
    var key = r.s + '|' + r.c;
    if(!bestByKey[key] || r.p < bestByKey[key].p) bestByKey[key] = r;
  });
  var rows = Object.keys(bestByKey).map(function(k){ return bestByKey[k]; });
  rows.sort(function(a,b){ return a.p - b.p; });
  rows = rows.slice(0, 6);
  var minP = rows.length ? rows[0].p : 0;
  list.innerHTML = rows.map(function(r){
    var u = r.u === 'per_cbm' ? '/CBM' : '/kg';
    var t = (r.t_min && r.t_max) ? (r.t_min + '-' + r.t_max + '天') : '—';
    var best = (r.p === minP) ? '<span class="q-best-tag">最低</span>' : '';
    return '<div class="q-row' + (r.p === minP ? ' best' : '') + '">' +
      '<div class="q-sup">' + r.s + '<span class="raw">' + r.c + ' · ' + (r.dd||'') + '</span></div>' +
      '<div class="q-ch">' + r.c + '</div>' +
      '<div class="q-rate num">' + r.p.toFixed(2) + '<span class="u">' + u + '</span></div>' +
      '<div class="q-time num">' + t + '</div>' +
      '<div class="q-in">' + r.inbound + ' · ' + r.wt + 'KG+' + best + '</div>' +
      '</div>';
  }).join('');
}

/* ===== 趋势：数据驱动分组重绘 ===== */
var TREND_WEEKS = ['第29周','第30周','第31周','第32周'];
var TREND_SERIES = {
  kp: [
    {name:'普船特惠卡派', color:'#0071e3', data:[5.42,5.30,5.24,5.21]},
    {name:'普船卡派',     color:'#30b352', data:[6.01,5.88,5.79,5.70]}
  ],
  fast: [
    {name:'美森CLX正班卡派', color:'#ff9f0a', data:[9.72,9.63,9.55,9.48]},
    {name:'美森MAX加班卡派', color:'#ff3b30', data:[8.36,8.31,8.20,8.14]}
  ]
};
var _trendGroup = 'kp';
function drawTrendGrid(group){
  _trendGroup = group || 'kp';
  var svg = document.getElementById('trendSvg');
  if(!svg) return;
  var series = TREND_SERIES[_trendGroup] || TREND_SERIES.kp;
  var legend = document.getElementById('trendLegend');
  if(legend){
    legend.innerHTML = series.map(function(s){
      return '<span class="trend-lg"><span class="sw" style="background:' + s.color + '"></span>' + s.name + '</span>';
    }).join('');
  }
  var W=900, H=300, padL=46, padR=20, padT=24, padB=34;
  var all = [];
  series.forEach(function(s){ all = all.concat(s.data); });
  var yMin = Math.floor(Math.min.apply(null, all)) - 1;
  var yMax = Math.ceil(Math.max.apply(null, all)) + 1;
  var x = function(i){ return padL + (W - padL - padR) * (i / (TREND_WEEKS.length - 1)); };
  var y = function(v){ return padT + (H - padT - padB) * (1 - (v - yMin) / (yMax - yMin)); };
  var g = '';
  var step = (yMax - yMin) >= 6 ? 2 : 1;
  for(var v=yMin; v<=yMax; v+=step){
    var yy=y(v);
    g += '<line x1="'+padL+'" y1="'+yy+'" x2="'+(W-padR)+'" y2="'+yy+'" stroke="rgba(0,0,0,.06)" stroke-width="1"/>';
    g += '<text x="'+(padL-10)+'" y="'+(yy+4)+'" text-anchor="end" font-size="11" fill="#aeaeb2" font-family="-apple-system,sans-serif">'+v+'</text>';
  }
  TREND_WEEKS.forEach(function(w,i){
    g += '<text x="'+x(i)+'" y="'+(H-12)+'" text-anchor="middle" font-size="12" fill="#aeaeb2" font-family="-apple-system,sans-serif">'+w+'</text>';
  });
  series.forEach(function(s){
    var pts = s.data.map(function(v,i){ return [x(i), y(v)]; });
    var line = pts.map(function(p,i){ return (i===0?'M':'L')+p[0].toFixed(1)+' '+p[1].toFixed(1); }).join(' ');
    var area = line + ' L ' + pts[pts.length-1][0] + ' ' + (H-padB) + ' L ' + pts[0][0] + ' ' + (H-padB) + ' Z';
    g += '<path d="'+area+'" fill="'+s.color+'" opacity=".06"/>';
    g += '<path d="'+line+'" fill="none" stroke="'+s.color+'" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>';
    pts.forEach(function(p){
      g += '<circle cx="'+p[0]+'" cy="'+p[1]+'" r="4" fill="#fff" stroke="'+s.color+'" stroke-width="2.5"/>';
    });
    var last = pts[pts.length-1];
    g += '<text x="'+last[0]+'" y="'+(last[1]-10)+'" text-anchor="middle" font-size="12" font-weight="700" fill="'+s.color+'" font-family="-apple-system,sans-serif">'+s.data[s.data.length-1].toFixed(2)+'</text>';
  });
  svg.innerHTML = g;
}

/* ===== 事件绑定与初始渲染 ===== */
(function(){
  var qBtn = document.getElementById('qBtn');
  var qInput = document.getElementById('qInput');
  function doQ(){ queryWarehouse(qInput ? qInput.value : (Object.keys(DEMO_WH_KEYS)[0])); }
  if(qBtn) qBtn.addEventListener('click', doQ);
  if(qInput) qInput.addEventListener('keydown', function(e){ if(e.key==='Enter') doQ(); });
  // 默认查询第一个仓
  if(qInput) qInput.value = Object.keys(DEMO_WH_KEYS)[0];
  doQ();
  // 趋势分组切换
  document.querySelectorAll('[data-tgrp]').forEach(function(t){
    t.addEventListener('click', function(){
      document.querySelectorAll('[data-tgrp]').forEach(function(x){ x.classList.remove('on'); });
      t.classList.add('on');
      drawTrendGrid(t.getAttribute('data-tgrp'));
    });
  });
  drawTrendGrid('kp');
})();
</script>
""" % {"wh": wh_json, "us": demo_json}

# 在 </body> 前注入
A = A.replace("</body>", inject_script + "\n</body>")

# ---- 5) demo-header hint 脱敏 ----
A = A.replace('<span class="hint">真实数据 · ONT8 演示</span>',
              '<span class="hint">演示数据 · 已脱敏</span>')

# ---- 6) 去掉 p-query 默认 readonly 的旧 value（已在新块覆盖）----

open(OUT_PATH, "w", encoding="utf-8").write(A)
print("OK -> %s" % OUT_PATH)
print("暴露仓库映射:", SUM_MAP)
print("demo 记录数:", len(demo))
print("输出大小: %.1f KB" % (len(A.encode('utf-8')) / 1024))
