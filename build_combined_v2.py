#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合成脚本 v2（阶段二：完成剩余 6 个 panel + 全页脱敏）
========================================================
在 v1（p-query / p-trend 已真交互）基础上，把剩余 6 个静态 panel 全部做成真交互：
  p-rank / p-screenshot / p-audit / p-monitor / p-score / p-weekly
并做全页脱敏（US-001）。

【复用 v1】p-query（输入 SUM 码 → 过滤虚拟数据 → 渲染最低价行）、p-trend（卡派/快船分组数据驱动重绘）
——这两处直接复刻 v1 逻辑，不推翻。
【修复 v1 隐患】v1 的趋势分组用了 `.demo-tab`，与全局 panel-tab 切换冲突（点趋势分组会把所有 `.demo-panel` 的 'on' 清掉 → 演示区空白）。
  本版把「panel 内」所有分组切换改为 `.pill`（与 `.demo-tab` 隔离），全局 `data-panel` 切 tab 不受影响。
【脱敏词汇表】
  - 供应商：复用母本B 虚拟名（云帆国际/顺达集运/星辰速运/蓝海物流/启航物流/通达国际/宏图跨境/远洋供应链）
  - 仓码：SUM1..SUM6
  - 量级单价：≈5-13元/kg（虚拟数据已满足）
  - 底价条数：8万+；通达仓码：600+；供应商：多家
【数据源】全部由 DEMO_US（母本B 脱敏映射）派生，monitor/score 同样由它计算，保证单一事实来源、可复现。
【约束】只读 demo_package + 母本；不改 internal-showcase / price-query。
"""
import json
import re
import sys
from collections import Counter, defaultdict

A_PATH = "/app/working/workspaces/NXUwKg/media/FreightGo_项目展示页_AIPM投递版_20260831.html"
B_PATH = "/app/working/workspaces/NXUwKg/demo_package/index.html"
OUT_PATH = "/app/working/workspaces/NXUwKg/demo_package/showcase_combined.html"

N = 6  # 暴露仓库数量 → SUM1..SUM6


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

# ---------- 暴露仓库映射（复用 v1） ----------
cnt = Counter(r["w"] for r in us)
wheels = [w for w, _ in cnt.most_common(N)]
wheels_sorted = sorted(wheels)
SUM_MAP = {w: "SUM%d" % (i + 1) for i, w in enumerate(wheels_sorted)}
GEO_TAG = "演示仓"

demo = []
for r in us:
    if r["w"] not in SUM_MAP:
        continue
    demo.append({
        "w": SUM_MAP[r["w"]],
        "s": r["s"], "c": r["c"], "wt": r["wt"], "p": r["p"],
        "u": r["u"], "dd": r["dd"], "inbound": r["inbound"],
        "t_min": r["t_min"], "t_max": r["t_max"],
    })
demo.sort(key=lambda r: (r["w"], r["c"], r["s"], r["wt"]))
demo_json = json.dumps(demo, ensure_ascii=False, separators=(",", ":"))

# 暴露仓库的 SUM 码 → 中性内部标识（真实 Amazon 仓码不出现在产物中，仅 SUM 码面向用户）
wh_keys = {SUM_MAP[w]: ("D%d" % (i + 1)) for i, w in enumerate(wheels_sorted)}
wh_json = json.dumps(wh_keys, ensure_ascii=False, separators=(",", ":"))

# 全部渠道（排序去重）
CHANNELS = sorted({r["c"] for r in us})
channels_json = json.dumps(CHANNELS, ensure_ascii=False, separators=(",", ":"))

# ---------- MONITOR：由 DEMO_US 派生（本周=min 档位价，old=确定性偏移） ----------
def _hashv(s):
    return sum(ord(ch) for ch in s)


def monitor_build(us_demo, channels):
    snap = {}
    for ch in channels:
        per_sup = {}
        for r in us_demo:
            if r["c"] != ch:
                continue
            cur = per_sup.get(r["s"])
            if cur is None or r["p"] < cur:
                per_sup[r["s"]] = r["p"]
        if not per_sup:
            continue
        rows = []
        for s, cur in per_sup.items():
            h = _hashv(s + ch)
            delta = round(0.05 + (h % 24) / 100.0, 2)  # 0.05 ~ 0.28
            up = (h % 2) == 0
            old = round(cur - delta, 2) if up else round(cur + delta, 2)
            rows.append({"s": s, "cur": cur, "old": old, "d": round(cur - old, 2)})
        # 按 |delta| 降序
        rows.sort(key=lambda x: abs(x["d"]), reverse=True)
        snap[ch] = rows
    return snap

MONITOR_SNAP = monitor_build(demo, ["普船特惠卡派", "普船卡派", "纽约卡派", "美森CLX正班"])
mon_json = json.dumps(MONITOR_SNAP, ensure_ascii=False, separators=(",", ":"))

# ---------- SCORE：由 DEMO_US 派生（价格/时效/覆盖/稳定 四维） ----------
def score_build(us_demo, total_wh, total_ch):
    per_sup = defaultdict(lambda: {"prices": [], "t": [], "wh": set(), "ch": set()})
    for r in us_demo:
        agg = per_sup[r["s"]]
        agg["prices"].append(r["p"])
        agg["t"].append((r["t_min"] + r["t_max"]) / 2.0)
        agg["wh"].add(r["w"])
        agg["ch"].add(r["c"])
    supps = sorted(per_sup.keys())
    # 均价比/均时效
    avg_p = {s: sum(v["prices"]) / len(v["prices"]) for s, v in per_sup.items()}
    avg_t = {s: sum(v["t"]) / len(v["t"]) for s, v in per_sup.items()}
    pmin, pmax = min(avg_p.values()), max(avg_p.values())
    tmin, tmax = min(avg_t.values()), max(avg_t.values())

    def _norm(v, lo, hi, lower_better=True):
        if hi - lo < 1e-9:
            return 60.0
        r = (v - lo) / (hi - lo)
        return (1.0 - r) * 100 if lower_better else r * 100

    rows = []
    for s in supps:  # noqa
        v = per_sup[s]
        price = round(_norm(avg_p[s], pmin, pmax, True), 1)
        time = round(_norm(avg_t[s], tmin, tmax, True), 1)
        cov = round(min(1.0, len(v["wh"]) / total_wh) * 55 + min(1.0, len(v["ch"]) / total_ch) * 45, 1)
        stab = round(70 + (_hashv(s) % 26), 1)
        total = round(price * 0.40 + time * 0.25 + cov * 0.20 + stab * 0.15, 1)
        rows.append({"s": s, "price": price, "time": time, "cov": cov, "stab": stab, "total": total})
    rows.sort(key=lambda x: x["total"], reverse=True)
    return rows

SCORE_DATA = score_build(demo, N, len(CHANNELS))
score_json = json.dumps(SCORE_DATA, ensure_ascii=False, separators=(",", ":"))

# ---------- 工具：按注释边界切片替换 panel ----------
def replace_panel(A, start_comment, end_marker):
    """start_comment 为 '<!-- XX -->'；end_marker 为下一个注释或固定串（取其后紧跟的 panel）。"""
    s = A.index(start_comment)
    e = A.index(end_marker, s)
    return s, e


# ========== 1) p-query：复刻 v1 ==========
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

# ========== 2) p-trend：复刻 v1 legend 替换（分组改为 .pill 避免与 .demo-tab 冲突） ==========
trend_legend_old = '''          <div class="trend-legend">
            <span class="trend-lg"><span class="sw" style="background:#0071e3"></span>普船特惠卡派</span>
            <span class="trend-lg"><span class="sw" style="background:#30b352"></span>普船卡派</span>
            <span class="trend-lg"><span class="sw" style="background:#ff9f0a"></span>美森CLX正班卡派</span>
            <span class="trend-lg"><span class="sw" style="background:#ff3b30"></span>美森MAX加班卡派</span>
          </div>'''
trend_legend_new = '''          <div class="demo-action" style="margin-bottom:14px">
            <span style="font-size:12px;color:var(--sub);font-weight:600;letter-spacing:.05em">趋势分组</span>
            <span class="pill on" data-tgrp="kp">卡派系列</span>
            <span class="pill" data-tgrp="fast">快船系列</span>
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

# ========== 3) 替换 drawTrend IIFE 为占位 ==========
dt_start = A.index("(function drawTrend(){")
dt_end = A.index("})();", dt_start) + len("})();")
A = A[:dt_start] + "/* 趋势图由下方注入脚本的数据驱动 drawTrendGrid 渲染 */" + A[dt_end:]

# ========== 4) p-rank：静态块 → 交互容器 ==========
rs, re_ = replace_panel(A, "        <!-- 智能比价 -->", "        <!-- 截图报价 -->")
rank_new = '''        <!-- 智能比价（合成：真交互，选仓点/渠道组 → Top3 比价卡） -->
        <div class="demo-panel" id="p-rank">
          <div class="demo-action" style="margin-bottom:6px">
            <span class="ctrl-label">仓点</span>
            <span class="ctrl" id="rankWhCtrl"></span>
            <span class="ctrl-label" style="margin-left:14px">渠道组</span>
            <span class="ctrl" id="rankCgCtrl"></span>
          </div>
          <div class="rk-grid" id="rankGrid"></div>
        </div>

'''
A = A[:rs] + rank_new + A[re_:]

# ========== 5) p-screenshot：静态块 → 剧本化交互 ==========
rs, re_ = replace_panel(A, "        <!-- 截图报价 -->", "        <!-- 报价校验 -->")
shot_new = '''        <!-- 截图报价（合成：剧本化交互：OCR→白名单校验→疑似确认→出报价） -->
        <div class="demo-panel" id="p-screenshot">
          <div class="ocr-flow">
            <span class="ocr-step"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M4 5h16v14H4z"/><path d="M9 12h6M9 9h3"/></svg>识别截图</span>
            <span class="ocr-arr">→</span>
            <span class="ocr-step"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M9 11l3 3 8-8"/><path d="M20 12v6a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h9"/></svg>白名单校验</span>
            <span class="ocr-arr">→</span>
            <span class="ocr-step"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3H5a1 1 0 0 0-1 1v3"/><path d="M16 3h3a1 1 0 0 1 1 1v3"/><path d="M8 21H5a1 1 0 0 1-1-1v-3"/><path d="M16 21h3a1 1 0 0 0 1-1v-3"/><path d="M10 15l2 2 4-4"/></svg>直接出报价</span>
            <span class="ocr-note">形近字符 O/0、I/1 存疑 → 列出候选让用户确认，不硬报</span>
          </div>
          <div class="demo-action" style="margin:16px 0 10px">
            <button id="shotReplay" class="shot-btn">▶ 重放识别</button>
            <span id="shotStatus" class="shot-status">示例：识别一张含「SUM1 / SUMI」仓码的报价截图</span>
          </div>
          <div id="shotStage" class="stg" style="background:var(--bg-2);border:1px solid var(--border);border-radius:14px;padding:18px 20px"></div>
        </div>

'''
A = A[:rs] + shot_new + A[re_:]

# ========== 6) p-audit：静态块 → 三道闸剧本 ==========
rs, re_ = replace_panel(A, "        <!-- 报价校验 -->", "        <!-- 价格监控 -->")
audit_new = '''        <!-- 报价校验（合成：三道闸剧本：拦报错价/纯底价/不该接直接拒） -->
        <div class="demo-panel" id="p-audit">
          <div class="demo-action" style="margin-bottom:14px">
            <span class="ctrl-label">选择票样</span>
            <span class="ctrl" id="auditScnCtrl"></span>
            <button id="auditRun" class="shot-btn" style="margin-left:6px">运行三道闸</button>
          </div>
          <div id="auditStage" class="stg"></div>
        </div>

'''
A = A[:rs] + audit_new + A[re_:]

# ========== 7) p-monitor：静态块 → 真交互（涨跌/告警/价差由 DEMO_US 派生） ==========
rs, re_ = replace_panel(A, "        <!-- 价格监控 -->", "        <!-- 供应商评分 -->")
mon_new = '''        <!-- 价格监控（合成：真交互：渠道/周期切换 → 涨价榜/降价榜/价差/异常告警） -->
        <div class="demo-panel" id="p-monitor">
          <div class="mon-head">
            <span class="mon-title"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 17l6-6 4 4 8-8"/><path d="M21 3v5h-5"/></svg><span id="monTitle">本周价格变动 · 普船特惠卡派</span></span>
            <span class="mon-sub" id="monSub"></span>
          </div>
          <div class="demo-action" style="margin-bottom:10px">
            <span class="ctrl-label">监控渠道</span>
            <span class="ctrl" id="monChCtrl"></span>
          </div>
          <div class="rk-grid" id="monGrid"></div>
          <div id="monAlerts"></div>
          <div class="mon-foot">价表入库自动对比，变动秒级推送，商务无需手动盯价。</div>
        </div>

'''
A = A[:rs] + mon_new + A[re_:]

# ========== 8) p-score：静态块 → 真交互（4 维加权，口径切换重排） ==========
rs, re_ = replace_panel(A, "        <!-- 供应商评分 -->", "        <!-- 价格趋势 -->")
score_new = '''        <!-- 供应商评分（合成：真交互：4 维加权，口径切换重排，Top3 高亮） -->
        <div class="demo-panel" id="p-score">
          <div class="score-head">
            <span class="mon-title"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l2.7 5.5 6.3.9-4.5 4.4 1 6.2-5.5-2.9L6 20l1-6.2L2.5 9.4l6.3-.9L12 3z"/></svg>供应商综合评分</span>
            <span class="mon-sub">价格 40% · 时效 25% · 覆盖 20% · 稳定 15%</span>
          </div>
          <div class="demo-action" style="margin-bottom:10px">
            <span class="ctrl-label">评分口径</span>
            <span class="ctrl" id="scoreDimCtrl"></span>
          </div>
          <div class="rk-grid" id="scoreGrid"></div>
          <div class="mon-foot">从「凭感觉选供应商」到「按可量化维度加权选型」，结果可溯源、可复现。</div>
        </div>

'''
A = A[:rs] + score_new + A[re_:]

# ========== 9) p-weekly：静态块 → 轻量交互（报告期切换 + 脱敏数值） ==========
ws = A.index("        <!-- 航运周报 -->")
WE_CLOSE = "\n\n      </div>\n    </div>\n  </div>\n</section>"
we = A.index(WE_CLOSE, ws)
weekly_new = '''        <!-- 航运周报（合成：轻量交互：本周/上周切换，数值已脱敏） -->
        <div class="demo-panel" id="p-weekly">
          <div class="demo-action" style="margin-bottom:14px">
            <span class="ctrl-label">报告期</span>
            <span class="ctrl" id="weeklyCycleCtrl"></span>
          </div>
          <div id="weeklyGrid" class="weekly-grid"></div>
        </div>

'''
A = A[:ws] + weekly_new + A[we:]

# ========== 10) 注入 CSS + 大数据脚本 ==========
extra_css = '''
/* 合成交互补充样式 */
.demo-action{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.ctrl{display:inline-flex;flex-wrap:wrap;gap:8px;align-items:center}
.ctrl-label{font-size:12px;color:var(--sub);font-weight:600;letter-spacing:.04em}
.pill{font-size:12px;padding:6px 14px;border:1px solid var(--border);border-radius:20px;background:var(--bg);color:var(--text);cursor:pointer;transition:all .15s ease;user-select:none}
.pill.on{background:var(--text);color:#fff;border-color:var(--text)}
.pill:hover:not(.on){border-color:var(--ac);color:var(--ac)}
.pill-link{font-size:12px;font-weight:600;color:var(--ac);cursor:pointer;background:none;border:none;padding:6px 2px}
.pill-link:hover{text-decoration:underline}
.shot-btn{font-size:13px;font-weight:600;color:#fff;background:var(--ac);border:none;border-radius:10px;padding:8px 16px;cursor:pointer;transition:all .15s ease;font-family:inherit}
.shot-btn:hover{transform:scale(1.03);filter:brightness(.98)}
.shot-btn[disabled]{opacity:.5;cursor:default;transform:none}
.shot-btn.ghost{background:var(--bg);color:var(--ac);border:1px solid var(--ac)}
.stg{font-size:13.5px;line-height:1.7;color:var(--text)}
.stg b{color:var(--ac)}
.stg .ok{color:#1a7f37;font-weight:700}
.stg .warn{color:#d0342c;font-weight:700}
.stg .muted{color:var(--sub)}
.stg-line{display:flex;gap:10px;align-items:baseline;padding:7px 0;border-bottom:1px dashed var(--border)}
.stg-line:last-child{border-bottom:none}
.stg-tag{display:inline-block;padding:2px 8px;border-radius:7px;font-size:11px;font-weight:700;margin-right:4px}
.mrow{display:flex;align-items:center;gap:10px;padding:9px 0;border-bottom:1px solid var(--border);font-size:13px}
.mrow:last-child{border-bottom:none}
.mrow .mtitle{font-weight:600;flex:1}
.mrow .mval{font-weight:700;font-variant-numeric:tabular-nums}
.mup{color:#d0342c}.mdn{color:#1a7f37}
.chtag{font-size:11px;font-weight:700;color:var(--sub);background:rgba(0,0,0,.05);padding:2px 8px;border-radius:7px}
@media(max-width:560px){.stg-line{flex-wrap:wrap;gap:4px}}
.q-search input{min-width:0}
.q-search button{flex:0 0 auto}
@media(max-width:560px){.q-search{flex-wrap:nowrap}.q-search input{font-size:14px;padding:12px 14px}.q-search button{padding:12px 16px;font-size:14px}}
'''

inject = """<style>%CSS%</style>
<script>
/* ===== 合成注入：虚拟数据（脱敏） ===== */
var DEMO_WH_KEYS = @@WH@@;
var DEMO_US = @@US@@;
var DEMO_GEO = "演示仓";
var ALL_CHANNELS = @@CH@@;
var MONITOR_SNAP = @@MON@@;
var SCORE_DATA = @@SCORE@@;

/* ===== 查价（复用 v1） ===== */
function queryWarehouse(raw){
  var code = (raw||'').trim().toUpperCase();
  var list = document.getElementById('qList');
  var head = document.getElementById('qHead');
  if(!list) return;
  if(!code){ list.innerHTML = '<div class="q-row" style="justify-content:center;color:var(--muted)">输入仓码开始查价</div>'; return; }
  var meta = null;
  for(var k in DEMO_WH_KEYS){ if(k===code){ meta=k; break; } }
  if(!meta){
    list.innerHTML = '<div class="q-row" style="justify-content:center;color:var(--muted)">未找到该仓码，可试：' + Object.keys(DEMO_WH_KEYS).join(' / ') + '</div>';
    return;
  }
  var whEl = document.getElementById('qWh');
  if(whEl) whEl.innerHTML = meta + ' <span class="q-wh-badge">' + DEMO_GEO + '</span>';
  var recs = DEMO_US.filter(function(r){ return r.w === meta; });
  if(!recs.length){ list.innerHTML = '<div class="q-row" style="justify-content:center;color:var(--muted)">该仓暂无价格数据</div>'; return; }
  var bestByKey = {};
  recs.forEach(function(r){ var k = r.s + '|' + r.c; if(!bestByKey[k] || r.p < bestByKey[k].p) bestByKey[k] = r; });
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
      '<div class="q-in">' + r.inbound + ' · ' + r.wt + 'KG+' + best + '</div></div>';
  }).join('');
}

/* ===== 趋势（复用 v1，分组用 .pill） ===== */
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
  if(legend) legend.innerHTML = series.map(function(s){ return '<span class="trend-lg"><span class="sw" style="background:' + s.color + '"></span>' + s.name + '</span>'; }).join('');
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
  TREND_WEEKS.forEach(function(w,i){ g += '<text x="'+x(i)+'" y="'+(H-12)+'" text-anchor="middle" font-size="12" fill="#aeaeb2" font-family="-apple-system,sans-serif">'+w+'</text>'; });
  series.forEach(function(s){
    var pts = s.data.map(function(v,i){ return [x(i), y(v)]; });
    var line = pts.map(function(p,i){ return (i===0?'M':'L')+p[0].toFixed(1)+' '+p[1].toFixed(1); }).join(' ');
    var area = line + ' L ' + pts[pts.length-1][0] + ' ' + (H-padB) + ' L ' + pts[0][0] + ' ' + (H-padB) + ' Z';
    g += '<path d="'+area+'" fill="'+s.color+'" opacity=".06"/>';
    g += '<path d="'+line+'" fill="none" stroke="'+s.color+'" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>';
    pts.forEach(function(p){ g += '<circle cx="'+p[0]+'" cy="'+p[1]+'" r="4" fill="#fff" stroke="'+s.color+'" stroke-width="2.5"/>'; });
    var last = pts[pts.length-1];
    g += '<text x="'+last[0]+'" y="'+(last[1]-10)+'" text-anchor="middle" font-size="12" font-weight="700" fill="'+s.color+'" font-family="-apple-system,sans-serif">'+s.data[s.data.length-1].toFixed(2)+'</text>';
  });
  svg.innerHTML = g;
}

/* ===== 通用：pill 渲染 ===== */
function pills(el, items, cur, cb){
  if(!el) return;
  el.innerHTML = items.map(function(it){
    var val = it.v, lab = it.t;
    return '<span class="pill' + (val===cur?' on':'') + '" data-v="'+val+'">'+lab+'</span>';
  }).join('');
  el.querySelectorAll('.pill').forEach(function(p){
    p.addEventListener('click', function(){
      el.querySelectorAll('.pill').forEach(function(x){ x.classList.remove('on'); });
      p.classList.add('on');
      cb(p.getAttribute('data-v'));
    });
  });
}

/* ===== 智能比价 ===== */
var RANK_GROUPS = {
  kp: { label:'卡派系列', channels:['普船特惠卡派','普船卡派','纽约卡派'] },
  fast: { label:'快船系列', channels:['美森CLX正班','美森MAX加班','合德ZIM快提'] }
};
var _rankWh = Object.keys(DEMO_WH_KEYS)[0], _rankCg = 'kp', _rankExpand = {};
function renderRank(){
  var grid = document.getElementById('rankGrid');
  if(!grid) return;
  var channels = RANK_GROUPS[_rankCg].channels;
  var html = channels.map(function(ch){
    var recs = DEMO_US.filter(function(r){ return r.w === _rankWh && r.c === ch; });
    var bestByKey = {};
    recs.forEach(function(r){ var k = r.s; if(!bestByKey[k] || r.p < bestByKey[k].p) bestByKey[k] = r; });
    var rows = Object.keys(bestByKey).map(function(k){ return bestByKey[k]; });
    rows.sort(function(a,b){ return a.p - b.p; });
    var total = rows.length;
    var show = _rankExpand[ch] ? total : Math.min(3, total);
    var items = rows.slice(0, show).map(function(r, i){
      var m = ['m1','m2','m3'][i] || '';
      var gap = i===0 ? '' : ' 较最低 +' + (r.p - rows[0].p).toFixed(2);
      return '<div class="rk-item"><span class="rk-medal ' + m + '">' + (i+1) + '</span>' +
        '<span class="rk-sup">' + r.s + '<span class="raw">' + ch + ' · ' + (r.inbound||'') + ' · ' + r.wt + 'KG+</span></span>' +
        '<span class="rk-rate num">' + r.p.toFixed(2) + '<span class="u">元/kg' + gap + '</span></span></div>';
    }).join('');
    var more = total > 3 ? '<button class="pill-link" data-more="'+ch+'" type="button">' + (_rankExpand[ch] ? '收起 ▲' : '展开更多 (' + total + ') ▼') + '</button>' : '';
    return '<div class="rk-card"><h4>' + ch + '</h4>' + items + more + '</div>';
  }).join('');
  grid.innerHTML = html;
  grid.querySelectorAll('[data-more]').forEach(function(b){
    b.addEventListener('click', function(){
      _rankExpand[b.getAttribute('data-more')] = !_rankExpand[b.getAttribute('data-more')];
      renderRank();
    });
  });
}

/* ===== 截图报价（剧本化） ===== */
var _shotBuf = [], _shotTimers = [];
function _shotStatus(t){ var s=document.getElementById('shotStatus'); if(s) s.textContent=t; }
function _shotStage(h){ var b=document.getElementById('shotStage'); if(b) b.innerHTML=h; }
function _shotAppend(html){ _shotBuf.push(html); _shotStage(_shotBuf.join('<div style="height:8px"></div>')); }
function _shotReset(){ _shotBuf=[]; _shotTimers.forEach(function(t){ clearTimeout(t); }); _shotTimers=[]; }
function _shotQuery(wh){
  var rowsHtml = '';
  var recs = DEMO_US.filter(function(r){ return r.w === wh; });
  var best = {};
  recs.forEach(function(r){ var k=r.s+'|'+r.c; if(!best[k]||r.p<best[k].p) best[k]=r; });
  var rows = Object.keys(best).map(function(k){ return best[k]; });
  rows.sort(function(a,b){ return a.p-b.p; });
  rows = rows.slice(0,6);
  var minP = rows.length ? rows[0].p : 0;
  rowsHtml = rows.map(function(r){
    var u = r.u === 'per_cbm' ? '/CBM' : '/kg';
    var t = (r.t_min && r.t_max) ? (r.t_min + '-' + r.t_max + '天') : '—';
    var bestTag = (r.p === minP) ? '<span class="q-best-tag">最低</span>' : '';
    return '<div class="q-row' + (r.p===minP?' best':'') + '"><div class="q-sup">'+r.s+'<span class="raw">'+r.c+' · '+(r.dd||'')+'</span></div><div class="q-ch">'+r.c+'</div><div class="q-rate num">'+r.p.toFixed(2)+'<span class="u">'+u+'</span></div><div class="q-time num">'+t+'</div><div class="q-in">'+r.inbound+' · '+r.wt+'KG+'+bestTag+'</div></div>';
  }).join('');
  _shotStage('<div class="q-result-head" style="margin-bottom:10px"><span class="q-wh">'+wh+' <span class="q-wh-badge">'+DEMO_GEO+'</span></span><span style="font-size:13px;color:var(--muted)">报价截图识别结果 · 已完成白名单校验</span></div><div class="q-head"><span>供应商</span><span>渠道</span><span style="text-align:right">单价</span><span style="text-align:right">时效</span><span style="text-align:right">进仓地</span></div>' + rowsHtml);
}
function _bindShotConfirm(){
  var btn = document.getElementById('shotConfirm');
  if(!btn) return;
  btn.addEventListener('click', function(){ _shotBuf = []; _shotQuery('SUM1'); });
}
function _replay(){
  _shotReset();
  _shotStatus('正在识别报价截图…');
  _shotAppend('<div class="muted">读取图片 ……</div>');
  _shotTimers.push(setTimeout(function(){
    _shotAppend('<div class="stg-line"><span class="chtag">OCR</span>仓码 token：<b>SUM1</b>（美西）</div><div class="stg-line"><span class="chtag">OCR</span>仓码 token：<b>SUMI</b>（美西）</div>');
  }, 600));
  _shotTimers.push(setTimeout(function(){
    _shotAppend('<div class="stg-line"><span class="chtag">白名单</span>SUM1 → <span class="ok">可通过</span></div><div class="stg-line"><span class="chtag">白名单</span>SUMI → <span class="warn">未命中</span>，形近字符 I/1 存疑</div>');
  }, 1200));
  _shotTimers.push(setTimeout(function(){
    _shotAppend('<div class="stg-line"><span class="chtag">候选</span>编辑距离最相似：<b>SUM1</b>（距离 1，I 读作 1）</div><div class="stg-line muted">疑似仓码必须让用户确认，禁止硬报。下方点「确认 SUM1 → 出报价」。</div><div style="margin-top:12px"><button id="shotConfirm" class="shot-btn ghost">确认 SUM1 → 出报价</button></div>');
    _bindShotConfirm();
  }, 1800));
}

/* ===== 报价校验（三道闸） ===== */
var _auditCurVal = 'ok';
var AUDIT_SCN = {
  ok: { name:'正常货 · DDP 完整信息', gate1:'pass', gate2:'pass', gate3:'pass' },
  size:{ name:'尺寸特长 · 长 >1.2m', gate1:'pass', gate2:'info', gate3:'pass' },
  bd: { name:'带电 · 禁运品', gate1:'pass', gate2:'pass', gate3:'block' }
};
function auditRun(key){
  var scn = AUDIT_SCN[key];
  var out = '<div class="audit-top" style="margin-bottom:16px">';
  var mw = [
    {l:'计费重量', v:'52<span class="u" style="font-size:12px;color:var(--sub)">kg</span>', d:'max(实重 48, 体积重 52)，1CBM=363KG'},
    {l:'比重优惠', v:'0.72<span class="u" style="font-size:12px;color:var(--sub)">元/kg</span>', d:'实重/体积 = 0.92，命中比重优惠档'},
    {l:'附加费', v:'200<span class="u" style="font-size:12px;color:var(--sub)">元/票</span>', d:'报关费 200 元/票，其余逐条单列'}
  ];
  mw.forEach(function(m){ out += '<div class="audit-metric"><div class="wlabel">'+m.l+'</div><div class="wval num">'+m.v+'</div><div class="wdesc">'+m.d+'</div></div>'; });
  out += '</div>';
  out += '<div class="q-head" style="margin-top:6px"><span>费用项</span><span>取值</span><span style="text-align:right">单位金额</span><span style="text-align:right">说明</span><span style="text-align:right">是否纳入</span></div>';
  var rows = [
    ['基础运费','5.30元/kg','5.30','按重量段','yes'],
    ['比重折扣','−0.72元/kg','−0.72','明码标价','yes'],
    ['报关费','200元/票','200','每票','yes']
  ];
  rows.forEach(function(r){ out += '<div class="audit-row"><div>'+r[0]+'</div><div>'+r[1]+'</div><div style="text-align:right" class="num">'+r[2]+'</div><div style="text-align:right">'+r[3]+'</div><div style="text-align:right"><span class="audit-badge '+(r[4]==='yes'?'yes':'info')+'">纳入</span></div></div>'; });
  // 三道闸
  var gates = '<div style="margin-top:14px;padding:16px;border:1px solid var(--border);border-radius:14px;background:var(--bg-2)"><div style="font-size:13px;font-weight:700;margin-bottom:10px">三道闸校验</div>';
  var g1 = scn.gate1, g2 = scn.gate2, g3 = scn.gate3;
  gates += gateLine('闸一 · 拦报错价', g1=== 'pass', '单价与带宽正常，无异常值', '单价 5.30 落在合理区间，无超阈值/单位错判');
  gates += gateLine('闸二 · 纯底价', g2==='pass', '附加费已单列，未自动加价', g2==='info' ? '尺寸附加费未计入——需提供尺寸，如实提示，绝不自动加价' : '附加费已单列，未自动加价');
  gates += gateLine('闸三 · 不该接直接拒', g3==='pass', '可正常承接', g3==='block' ? '带电/禁运 → 拒绝，并给出替代方向（改走空运专线/换合规品名）' : '可正常承接');
  gates += '</div>';
  out += gates;
  // 结论
  var verdict;
  if(g3==='block'){ verdict = '<div style="margin-top:12px;padding:12px 16px;border-radius:12px;background:rgba(208,52,44,.08);color:#d0342c;font-weight:700">✕ 不该接 → 直接拒：带电 / 禁运品，建议改走空运专线或换合规品名</div>'; }
  else if(g2==='info'){ verdict = '<div style="margin-top:12px;padding:12px 16px;border-radius:12px;background:rgba(0,113,227,.08);color:var(--ac);font-weight:700">⚠ 放行，但尺寸附加费待补——先给核心报价，尺寸信息补齐后再修正</div>'; }
  else { verdict = '<div style="margin-top:12px;padding:12px 16px;border-radius:12px;background:rgba(26,127,55,.08);color:#1a7f37;font-weight:700">✓ 三道闸通过 → 放行报价</div>'; }
  out += verdict;
  out += '<div class="audit-note">铁律：附加费逐条列出、不堆总价；自动核对单价±比重±附加费，绝不自动加价——宁可不报价，不可报错价。</div>';
  var b = document.getElementById('auditStage');
  if(b) b.innerHTML = out;
}
function gateLine(title, ok, okMsg, elseMsg){
  var cls = ok ? 'ok' : 'warn';
  var txt = ok ? ('通过 · ' + okMsg) : ('拦截 · ' + elseMsg);
  return '<div class="stg-line"><span class="chtag" style="'+(ok?'color:#1a7f37':'color:#d0342c')+'">'+(ok?'✓':'✕')+'</span><span class="muted" style="flex:1">' + title + '</span><span class="' + cls + '">' + txt + '</span></div>';
}

/* ===== 价格监控（真交互） ===== */
var _monCh = '普船特惠卡派';
function renderMon(ch){
  _monCh = ch || '普船特惠卡派';
  var rows = MONITOR_SNAP[_monCh] || [];
  var grid = document.getElementById('monGrid');
  var t = document.getElementById('monTitle');
  var sub = document.getElementById('monSub');
  function movers(dir){
    var arr = rows.filter(function(r){ return (dir>0 ? r.d>0 : r.d<0); });
    return arr.slice(0,3);
  }
  function card(title, arr, isUp){
    var items = arr.map(function(r,i){
      var m = ['m1','m2','m3'][i]||'';
      var cls = isUp ? 'mup' : 'mdn';
      var arrow = isUp ? '↑' : '↓';
      return '<div class="rk-item"><span class="rk-medal '+m+'">'+(i+1)+'</span><span class="rk-sup">'+r.s+'<span class="raw">'+arrow+' ' + Math.abs(r.d).toFixed(2) + ' 元/kg（'+ r.old.toFixed(2) +' → '+ r.cur.toFixed(2) +'）</span></span><span class="rk-rate num" style="color:'+(isUp?'#d0342c':'#1a7f37')+'">'+r.cur.toFixed(2)+'</span></div>';
    }).join('');
    return '<div class="rk-card"><h4>'+title+'</h4>'+(items||'<div class="muted" style="font-size:13px">暂无</div>')+'</div>';
  }
  var ups = movers(1), downs = movers(-1);
  // 价差最大：同渠道高低价差
  var byPrice = rows.slice().sort(function(a,b){ return b.cur - a.cur; });
  var maxGap = rows.length ? (byPrice[0].cur - byPrice[byPrice.length-1].cur) : 0;
  var spread = '<div class="rk-card"><h4>价差最大</h4><div class="rk-item"><span class="rk-medal m1">1</span><span class="rk-sup">'+_monCh+'<span class="raw">同供应商高低价差 '+maxGap.toFixed(2)+' 元/kg</span></span><span class="rk-rate num">'+maxGap.toFixed(2)+'</span></div></div>';
  grid.innerHTML = card('涨价榜', ups, true) + card('降价榜', downs, false) + spread;
  if(t) t.textContent = '本周价格变动 · ' + _monCh;
  if(sub) sub.textContent = rows.length + ' 家供应商报价异动';
  var alerts = document.getElementById('monAlerts');
  var worst = rows.filter(function(r){ return Math.abs(r.d) >= 0.20; }).sort(function(a,b){ return Math.abs(b.d)-Math.abs(a.d); });
  if(alerts){
    alerts.innerHTML = worst.length ? '<div style="margin-top:14px;padding:12px 16px;border-radius:12px;background:rgba(208,52,44,.08);color:#d0342c;font-weight:700">⚠ 异常告警：' + worst.slice(0,2).map(function(r){ return r.s+' 波动 '+Math.abs(r.d).toFixed(2)+' 元/kg'; }).join('、') + '</div>' : '<div style="margin-top:14px;padding:12px 16px;border-radius:12px;background:rgba(26,127,55,.08);color:#1a7f37;font-weight:700">✓ 无异常告警</div>';
  }
}

/* ===== 供应商评分（真交互） ===== */
var _scoreDim = 'total';
var SCORE_DIMS = [
  {v:'total', t:'综合'}, {v:'price', t:'价格'}, {v:'time', t:'时效'}, {v:'cov', t:'覆盖'}, {v:'stab', t:'稳定'}
];
function renderScore(dim){
  _scoreDim = dim || 'total';
  var data = SCORE_DATA.slice();
  data.sort(function(a,b){ return b[_scoreDim] - a[_scoreDim]; });
  var grid = document.getElementById('scoreGrid');
  var dimLabel = {total:'综合', price:'价格', time:'时效', cov:'覆盖', stab:'稳定'}[_scoreDim];
  var top = data.slice(0,3);
  var cards = top.map(function(r, idx){
    var m = ['m1','m2','m3'][idx];
    var score = r[_scoreDim];
    var raw = _scoreDim === 'total' ? '综合评分 ' + r.total : dimLabel + '力 ' + score;
    var breakdown = '<div class="rk-item" style="border-bottom:none"><span style="font-size:11px;color:var(--sub)">价格 ' + r.price + ' · 时效 ' + r.time + ' · 覆盖 ' + r.cov + ' · 稳定 ' + r.stab + '</span></div>';
    return '<div class="rk-card"><h4>' + dimLabel + '第 ' + (idx+1) + '</h4>' +
      '<div class="rk-item"><span class="rk-medal '+m+'">'+(idx+1)+'</span><span class="rk-sup">'+r.s+'<span class="raw">' + raw + '</span></span><span class="rk-rate num">'+score.toFixed(1)+'</span></div>' + breakdown + '</div>';
  }).join('');
  grid.innerHTML = cards + rankCard(data.slice(3,6), dimLabel);
}
function rankCard(rows, dimLabel){
  if(!rows.length) return '';
  var items = rows.map(function(r,i){
    return '<div class="rk-item"><span class="rk-medal">'+(i+4)+'</span><span class="rk-sup">'+r.s+'<span class="raw">'+dimLabel+' '+r[_scoreDim].toFixed(1)+'</span></span><span class="rk-rate num">'+r[_scoreDim].toFixed(1)+'</span></div>';
  }).join('');
  return '<div class="rk-card" style="grid-column:1/-1"><h4>第 4–'+(rows.length+3)+' 名</h4>'+items+'</div>';
}

/* ===== 航运周报（轻量交互） ===== */
var WEEKLY = {
  this: [
    {l:'运价走势', v:'3,436', d:'↑ 4.67%', up:1, x:'SCFI 综合指数本周反弹，美西线领涨。'},
    {l:'全球运价', v:'4,712', d:'↑ 2.1%', up:1, x:'WCI 全球集装箱运价指数连续两周上行。'},
    {l:'本周概览', v:'8万+', d:'条底价', up:0, x:'多家供应商、600+ 通达仓码，实时更新。'},
    {l:'最优报价', v:'5.30', d:'元/kg', up:0, x:'SUM1 演示仓 · 虚拟供应商普船特惠卡派，51KG+ 起。'},
    {l:'市场预测', v:'稳中', d:'偏强', up:1, x:'旺季临近，运价预计维持震荡上行。'},
    {l:'重点关注', v:'800', d:'美元', up:0, x:'免税政策调整，低货值商品成本承压。'}
  ],
  last: [
    {l:'运价走势', v:'3,283', d:'—', up:0, x:'上周 SCFI 低位整理，本周反弹。'},
    {l:'全球运价', v:'4,615', d:'—', up:0, x:'上周 WCI 横盘，本周小幅上行。'},
    {l:'本周概览', v:'8万+', d:'条底价', up:0, x:'多家供应商、600+ 通达仓码，实时更新。'},
    {l:'最优报价', v:'5.42', d:'元/kg', up:0, x:'上周候选：SUM1 演示仓 · 普船特惠卡派。'},
    {l:'市场预测', v:'稳中', d:'偏强', up:0, x:'旺季临近，运价预计维持震荡上行。'},
    {l:'重点关注', v:'720', d:'美元', up:0, x:'上周免税政策窗口，报关口径待统一。'}
  ]
};
var _weekCycle = 'this';
function renderWeekly(cycle){
  _weekCycle = cycle || 'this';
  var arr = WEEKLY[_weekCycle];
  var g = document.getElementById('weeklyGrid');
  if(!g) return;
  g.innerHTML = arr.map(function(c){
    var dl = c.show_delta ? c.show_delta : (c.d ? '<span class="delta '+(c.up?'up':'')+'">' + c.d + '</span>' : '');
    return '<div class="weekly-card"><div class="wlabel">'+c.l+'</div><div class="wval num">'+c.v+dl+'</div><div class="wdesc">'+c.x+'</div></div>';
  }).join('');
}

/* ===== 初始化 ===== */
(function(){
  // 查价
  var qInput = document.getElementById('qInput');
  var qBtn = document.getElementById('qBtn');
  function doQ(){ queryWarehouse(qInput ? qInput.value : Object.keys(DEMO_WH_KEYS)[0]); }
  if(qBtn) qBtn.addEventListener('click', doQ);
  if(qInput) qInput.addEventListener('keydown', function(e){ if(e.key==='Enter') doQ(); });
  if(qInput) qInput.value = Object.keys(DEMO_WH_KEYS)[0];
  doQ();
  // 趋势
  document.querySelectorAll('[data-tgrp]').forEach(function(t){
    t.addEventListener('click', function(){
      document.querySelectorAll('[data-tgrp]').forEach(function(x){ x.classList.remove('on'); });
      t.classList.add('on');
      drawTrendGrid(t.getAttribute('data-tgrp'));
    });
  });
  drawTrendGrid('kp');

  // 智能比价
  var whCtrl = document.getElementById('rankWhCtrl');
  var cgCtrl = document.getElementById('rankCgCtrl');
  if(whCtrl) pills(whCtrl, Object.keys(DEMO_WH_KEYS).map(function(k){ return {v:k, t:k}; }), _rankWh, function(v){ _rankWh=v; renderRank(); });
  if(cgCtrl) pills(cgCtrl, [{v:'kp', t:'卡派系列'},{v:'fast', t:'快船系列'}], _rankCg, function(v){ _rankCg=v; renderRank(); });
  renderRank();

  // 截图报价
  var replayBtn = document.getElementById('shotReplay');
  if(replayBtn){
    replayBtn.addEventListener('click', function(){ _replay(); });
    document.getElementById('shotStatus').textContent = '示例：识别一张含「SUM1 / SUMI」仓码的报价截图';
    document.getElementById('shotStage').innerHTML = '<div class="muted">点击「重放识别」开始演示。</div>';
  }

  // 报价校验
  var scnCtrl = document.getElementById('auditScnCtrl');
  if(scnCtrl){
    pills(scnCtrl, Object.keys(AUDIT_SCN).map(function(k){ return {v:k, t:AUDIT_SCN[k].name}; }), 'ok', function(v){ _auditCurVal=v; auditRun(v); });
    var ar = document.getElementById('auditRun');
    if(ar) ar.addEventListener('click', function(){ auditRun(_auditCurVal); });
    auditRun('ok');
  }

  // 价格监控
  var monChCtrl = document.getElementById('monChCtrl');
  if(monChCtrl){
    var chs = Object.keys(MONITOR_SNAP);
    pills(monChCtrl, chs.map(function(ch){ return {v:ch, t:ch}; }), '普船特惠卡派', function(v){ renderMon(v); });
    renderMon('普船特惠卡派');
  }

  // 供应商评分
  var dimCtrl = document.getElementById('scoreDimCtrl');
  if(dimCtrl){
    pills(dimCtrl, SCORE_DIMS, 'total', function(v){ renderScore(v); });
    renderScore('total');
  }

  // 航运周报
  var wcCtrl = document.getElementById('weeklyCycleCtrl');
  if(wcCtrl){
    pills(wcCtrl, [{v:'this', t:'本周'},{v:'last', t:'上周'}], 'this', function(v){ renderWeekly(v); });
    renderWeekly('this');
  }
})();
</script>"""

# 用占位替换避免 %/{} 冲突
inject = inject.replace("%CSS%", extra_css)
inject = inject.replace("@@WH@@", wh_json)
inject = inject.replace("@@US@@", demo_json)
inject = inject.replace("@@CH@@", channels_json)
inject = inject.replace("@@MON@@", mon_json)
inject = inject.replace("@@SCORE@@", score_json)

A = A.replace("</body>", inject + "\n</body>")

# ========== 11) 全页脱敏（US-001） ==========
# hero / metric 底价条数 & 通达仓码 → 量级
A = A.replace('<div class="v"><span class="num" data-count="86520">0</span></div><div class="l">条底价沉淀</div>',
              '<div class="v"><span class="num">8万+</span></div><div class="l">条底价沉淀</div>')
A = A.replace('<div class="v"><span class="num" data-count="660">0</span></div><div class="l">个通达仓码</div>',
              '<div class="v"><span class="num">600+</span></div><div class="l">个通达仓码</div>')
A = A.replace('<div class="m-val"><span class="num" data-count="86520">0</span></div><div class="m-label">条底价</div>',
              '<div class="m-val"><span class="num">8万+</span></div><div class="m-label">条底价</div>')
A = A.replace('<div class="m-val"><span class="num" data-count="660">0</span></div><div class="m-label">个通达仓码覆盖</div>',
              '<div class="m-val"><span class="num">600+</span></div><div class="m-label">个通达仓码覆盖</div>')

# 供应商家数（真实为 24，脱敏为 8 家虚拟供应商，保持与 demo 数据一致）
A = A.replace('<span class="num" data-count="24">0</span></div><div class="l">家供应商接入',
              '<span class="num" data-count="8">0</span></div><div class="l">家供应商接入')
A = A.replace('<span class="num" data-count="24">0</span></div><div class="m-label">家供应商接入',
              '<span class="num" data-count="8">0</span></div><div class="m-label">家供应商接入')

# pain-points 段落的「24家供应商，各自一套价表格式」→ 8 家（与 demo 一致）
A = A.replace('>24</span><span class="t">家供应商，各自一套价表格式',
              '>8</span><span class="t">家供应商，各自一套价表格式')

# 真实数据演示 → 演示数据
A = A.replace('真实数据演示：从询价、比价、报价校验、到监控、评分、周报，覆盖商务每天的真实工作流。',
              '演示数据：从询价、比价、报价校验、到监控、评分、周报，覆盖商务每天的真实工作流。')

# hint 脱敏（v1 已做，这里在母本A 原始文本上再确保）
A = A.replace('<span class="hint">真实数据 · ONT8 演示</span>',
              '<span class="hint">演示数据 · 已脱敏</span>')

# outro meta：真实询价网页还原 / 生产系统实测 → 脱敏表述
A = A.replace('数据为生产系统实测 · 供应商与渠道名已脱敏 · 界面为真实询价网页还原',
              '演示数据 · 供应商与渠道名已脱敏 · 界面为产品演示还原')

open(OUT_PATH, "w", encoding="utf-8").write(A)
print("OK -> %s" % OUT_PATH)
print("SUM_MAP:", SUM_MAP)
print("demo 记录数:", len(demo))
print("monitor channels:", list(MONITOR_SNAP.keys()))
print("score suppliers:", len(SCORE_DATA))
print("输出大小: %.1f KB" % (len(A.encode('utf-8')) / 1024))

# 自检：确认脱敏残留
for term in ["文轩","美新","鼎邦","英美","讯合","腾信","星河","森磊","沃利","荣达","金飞旗","鸥吉通","联宇","天拓","盈和","锦联","乘风破浪","保宏","九方","巨人","陆行","速鋆","美伽","华宇","鑫海","ONT8","LAX9","LGB8","SBD1","ATL2","CMH3","HOU8","MKE1","ORD2","86520","8.2万","真实询价网页","24 家","24家","真实数据 ·"]:
    if term in A:
        print("[残留] %s" % term)
