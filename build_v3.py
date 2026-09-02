# -*- coding: utf-8 -*-
"""build_v3.py — V3 scroll-driven portfolio. Rebuilds index.html from:
   1. _styles_v3.css  (new visual system)
   2. _demo_css.css   (product-demo internal styles, kept)
   3. _prod_block.html(8-panel live product demo, kept as-is)
   Narrative sections are fully re-laid-out. GSAP ScrollTrigger drives animation.
"""
import io, re, os

HERE = os.path.dirname(os.path.abspath(__file__))

def read(fn):
    with io.open(os.path.join(HERE, fn), encoding='utf-8') as f:
        return f.read()

styles_v3 = read('_styles_v3.css')
demo_css  = read('_demo_css.css')
prod      = read('_prod_block.html')
tab_js    = read('_script_tab.js')
inject_js = read('_script_inject.js')

# ---------------------------------------------------------------------
# Narrative sections (all re-laid-out)
# ---------------------------------------------------------------------
NAV = '''
<header class="nav" id="nav">
  <a class="nav-logo" href="#top"><span class="dot">F</span>FreightGo</a>
  <nav class="nav-links">
    <a href="#duel">设计判断</a>
    <a href="#flow">工作流</a>
    <a href="#product">产品</a>
    <a href="#arch">架构</a>
    <a href="#guard">责任</a>
  </nav>
  <a class="nav-cta" href="#product">看系统演示</a>
</header>
<div class="progress" id="progress"></div>
'''

HERO = '''
<section class="hero noise" id="top">
  <canvas id="hero-canvas"></canvas>
  <div class="wrap">
    <h1 class="hero-title" id="hero-title">
      <span class="line grad">让每一次报价</span><br>
      <span class="line">都<span class="ac">有据可查</span></span>
    </h1>
    <p class="hero-lead">跨境物流商务每天面对几十张周更 Excel 价表，查一个仓库的底价要来回翻十几分钟，还容易报错价、漏要素。我没有止步于「让 AI 聊天」——而是把一个真问题拆解、落地、验证，做成一套能扛住真实业务压力的系统。</p>
    <div class="hero-chips">
      <span class="chip"><span class="ci ci-ci"></span>智能询价</span>
      <span class="chip"><span class="ci ci-shot"></span>截图识别</span>
      <span class="chip"><span class="ci ci-trend"></span>趋势判断</span>
      <span class="chip"><span class="ci ci-week"></span>周报聚合</span>
    </div>
    <div class="hero-actions">
      <a class="btn-primary" href="#product">看产品演示</a>
      <a class="btn-ghost" href="#duel">先看产品判断</a>
    </div>
    <div class="hero-stats">
      <div class="stat"><div class="num"><span data-count="8">8</span>万+</div><div class="lb">条底价沉淀</div></div>
      <div class="stat"><div class="num"><span data-count="24">24</span>家</div><div class="lb">供应商接入</div></div>
      <div class="stat"><div class="num"><span data-count="600">600</span>+</div><div class="lb">个通达仓码</div></div>
      <div class="stat"><div class="num"><em>&lt;1</em>秒</div><div class="lb">查询响应</div></div>
    </div>
  </div>
  <div class="scroll-hint"><div class="mouse"></div>Scroll</div>
</section>
'''

DUEL = '''
<section class="section duel noise" id="duel">
  <div class="duel-stage">
    <div class="wrap" style="width:100%">
      <div class="section-head" style="margin-bottom:clamp(40px,5vw,70px);max-width:760px">
        <span class="eyebrow">第一条产品判断</span>
        <h2 class="h-lg" style="margin-top:20px">AI 应该做什么，<br>绝不该做什么</h2>
        <p class="lead" style="margin-top:16px">我做的第一件事不是调大模型，而是判断——这个问题里，AI 适合做什么、绝不适合做什么。这是 AI 产品落地最容易被忽略、也最见功力的一步。</p>
      </div>
      <div class="duel-grid">
        <div class="duel-card duel-card--do">
          <span class="duel-tag">AI 该做的 · 感知</span>
          <h3>读得懂、抓得出、推荐得动</h3>
          <p>报价截图、非标准 Excel、模糊查询——这些允许误差、可以被规则兜住的输入，交给大模型，让机器学会「看」。</p>
          <ul class="items">
            <li><span class="ic">✓</span>客户甩来的报价截图 → 多模态逐字识别仓码与价格</li>
            <li><span class="ic">✓</span>各家格式迥异的价表 → 精确提取规则文本入库</li>
            <li><span class="ic">✓</span>模糊的查询意图 → 智能比价、趋势判断、周报聚合</li>
          </ul>
        </div>
        <div class="duel-arrow"><span class="ring">VS</span></div>
        <div class="duel-card duel-card--dont">
          <span class="duel-tag">AI 绝不能做的 · 算钱</span>
          <h3>一分不能差的事，交给确定性引擎</h3>
          <p>运费错一分就是真金白银的亏损。大模型最致命的不是不会算，而是——<strong style="color:var(--text)">一本正经地算错、还无法自证对错。</strong>这一环必须锁死。</p>
          <ul class="items">
            <li><span class="ic">✓</span>计费规则四维锁定，比重 / 附加费 / 报关费逐条核</li>
            <li><span class="ic">✓</span>仓码白名单 + 黑名单校验，绝不让模型「猜」</li>
            <li><span class="ic">✓</span>每条报价可溯源到原始价表，引擎只读底价不加价</li>
          </ul>
        </div>
      </div>
      <p class="duel-note">我的判断：AI 用于 <strong>容错</strong>，而不能用于 <strong>负责</strong>。</p>
    </div>
  </div>
</section>
'''



# ---------------------------------------------------------------------
PROBLEM = '''
<section class="section noise" id="problem">
  <div class="wrap">
    <div class="grid" style="grid-template-columns:1.1fr .9fr;align-items:start">
      <div>
        <span class="eyebrow">业务痛点</span>
        <h2 class="h-lg" style="margin-top:20px">报价，是商务最耗时<br>也最容易出错的一环</h2>
        <p class="lead" style="margin-top:18px;max-width:560px">价格散落在各家供应商的 Excel 里，口径五花八门。人工翻表，既慢又险。</p>
      </div>
      <div class="cards" style="grid-template-columns:1fr;gap:14px">
        <div class="card" style="grid-column:1">
          <span class="cnum">效率</span>
          <h4>查价慢</h4>
          <p>供应商价表按周更新、版本繁多，一个仓码要跨十几张表人工核对，单次询价耗时数分钟起。</p>
        </div>
        <div class="card" style="grid-column:1">
          <span class="cnum">口径</span>
          <h4>比价难</h4>
          <p>渠道命名、计费规则（重量段、比重、附加费、报关费）不统一，表面单价根本无法横向比较真实底价。</p>
        </div>
        <div class="card" style="grid-column:1">
          <span class="cnum">风险</span>
          <h4>报价乱</h4>
          <p>起运地、时效、附加费口径不一致，容易报错价、漏要素，直接影响成交与口碑。</p>
        </div>
      </div>
    </div>
  </div>
</section>
'''

APPROACH = '''
<section class="section noise" id="approach" style="background:var(--bg-2)">
  <div class="wrap">
    <div class="section-head" style="max-width:700px">
      <span class="eyebrow">落地策略</span>
      <h2 class="h-lg" style="margin-top:20px">把「能跑」推向「敢上生产」</h2>
      <p class="lead" style="margin-top:16px">我靠的不是模型，是判断。很多 demo 很惊艳，但一上生产就崩——原因只有一个：没想清楚「准确率是谁负责、容错谁来兜、出了错怎么溯源」。这三件事，我把它做成产品机制，而不是运气。</p>
    </div>
    <div class="cards" style="margin-top:56px">
      <div class="card">
        <div class="cico"><svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M9 12l2 2 4-4m5.6-1.6A9 9 0 116.9 4.4"/></svg></div>
        <span class="cnum">准确率</span>
        <h4>AI 可以「猜」，但必须有护栏</h4>
        <p>表面单价看似精确，真实成本却被计费规则、比重、附加费藏得深。我用「白名单 + 编辑距离 + 主动确认」三道闸，把模型对形近字符的随机误差挡在报价之外。</p>
      </div>
      <div class="card">
        <div class="cico"><svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M9 12l2 2 4-4m5.6-1.6A9 9 0 116.9 4.4"/></svg></div>
        <span class="cnum">可溯源</span>
        <h4>每条报价，都要能指回去</h4>
        <p>用户说「凭什么这个价」，我得能回答。渠道原始名、进仓点、适用重量段全部保真留存，报价可溯源到原始价表——这是信任的根基。</p>
      </div>
      <div class="card">
        <div class="cico"><svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg></div>
        <span class="cnum">底线</span>
        <h4>宁可不报价，不可报错价</h4>
        <p>引擎只读底价，禁止任何形式加价。准确率不是模型的功劳，是你敢不敢对它负责。</p>
      </div>
    </div>
  </div>
</section>
'''

# ---------------------------------------------------------------------
def _tl_segs():
    data = [
        ("01", "询价查询", "一个仓码，跨十几张价表", ["输入 SUM1 这样的仓码", "按最低单价排序，每渠道取最低档", "秒级返回，不需要翻表"]),
        ("02", "智能比价", "表面单价无法横向比", ["渠道母集标准化，归到统一命名", "选择仓点 / 渠道组", "给出 Top3 最优 + 点评"]),
        ("03", "截图报价", "客户甩张图，人工抄价慢", ["VLM 逐字 OCR 识别仓码与价格", "白名单校验，不是正则猜", "疑似仓码列候选让用户确认"]),
        ("04", "报价校验", "附加费漏算就亏钱", ["计费规则四维锁定", "比重 / 附加费 / 报关费逐条核", "引擎只读底价，绝不加价"]),
        ("05", "价格监控", "价表周更，盯不住涨跌", ["入库自动对比", "变动秒级推送告警", "商务无需手动盯价"]),
        ("06", "供应商评分", "凭感觉选供应商不靠谱", ["价格 / 时效 / 覆盖 / 稳定加权", "可溯源、可复现", "按可量化维度选型"]),
        ("07", "价格趋势", "涨还是跌，要有走势", ["SQL 快照对比", "逐周核对，数据可信", "趋势可查可回溯"]),
        ("08", "航运周报", "给商务一份决策依据", ["核心指数 / 航线走势聚合", "市场动态 / 下周预测 / 商务建议", "五点聚焦，先给结论"]),
    ]
    segs = []
    for n, title, sub, steps in data:
        lis = "".join('<li><span class="n">%s</span>%s</li>' % (i, s) for i, s in enumerate(steps, 1))
        segs.append('<div class="flow-item"><div class="tl-num">%s</div><div class="flow-body"><h3>%s</h3><p>%s</p><ul class="tl-steps">%s</ul></div></div>' % (n, title, sub, lis))
    return segs

FLOW = '''
<section class="section noise" id="flow">
  <div class="wrap">
    <div class="section-head" style="max-width:720px;margin-bottom:10px">
      <span class="eyebrow">主线走查</span>
      <h2 class="h-lg" style="margin-top:20px">一票货，从询价到成交</h2>
      <p class="lead" style="margin-top:16px">这才是商务每天真实发生的事。八个模块不是并列展示，而是嵌进一条完整的工作流里。</p>
    </div>
  </div>
  <div class="wrap">
    <div class="flow-list">%s</div>
  </div>
</section>
''' % "".join(_tl_segs())

# ---------------------------------------------------------------------
# 产品演示区 = 活的黑盒，保真保留（8 面板 + 注入脚本依赖的结构不动）
# 只把 section 外层 wrap 换成新视觉，内部 demo 结构原样
PRODUCT_AREA = prod

# ---------------------------------------------------------------------
ARCH = '''
<section class="section noise" id="arch" style="background:var(--bg-2)">
  <div class="wrap">
    <div class="grid" style="grid-template-columns:.9fr 1.1fr;gap:56px;align-items:start">
      <div>
        <span class="eyebrow">系统架构</span>
        <h2 class="h-lg" style="margin-top:20px">数据、规则、AI、展示<br>四层解耦，各自可验证</h2>
        <p class="lead" style="margin-top:18px">每一层独立验证、独立替换，新增供应商或线路，不碰既有结构。核心工程决策：三库分离防止测试污染生产；分线路分表从根上杜绝跨线路脏数据；渠道原始名与进仓点保真留存，报价可溯源；引擎只读底价、禁止加价。</p>
      </div>
      <div class="layers">
        <div class="layer"><span class="lnum">01</span><span class="lname">应用层</span><span class="ldesc">询价网页 · 价格对比表 · 趋势图 · 周报，单文件离线可用</span><span class="ltag">展示</span></div>
        <div class="layer"><span class="lnum">02</span><span class="lname">AI 层</span><span class="ldesc">截图 OCR（多模态）· 模型路由 · 多 Agent 编排</span><span class="ltag">感知</span></div>
        <div class="layer"><span class="lnum">03</span><span class="lname">引擎层</span><span class="ldesc">询价引擎 · 报价引擎 · 计费规则引擎</span><span class="ltag">决策</span></div>
        <div class="layer"><span class="lnum">04</span><span class="lname">解析层</span><span class="ldesc">统一入库 · 卡派 / 海派 / 时效 / 规则 / 船期，五模块全量验证</span><span class="ltag">摄入</span></div>
        <div class="layer"><span class="lnum">05</span><span class="lname">数据层</span><span class="ldesc">SQLite 三库分离（生产 / 测试 / 档案）· 分线路分表 · 配置集中化</span><span class="ltag">存储</span></div>
      </div>
    </div>
  </div>
</section>
'''

AI = '''
<section class="section noise" id="ai">
  <div class="wrap">
    <div class="section-head" style="max-width:720px">
      <span class="eyebrow">AI 能力</span>
      <h2 class="h-lg" style="margin-top:20px">AI 做感知，规则做决策</h2>
      <p class="lead" style="margin-top:16px">大模型可以猜，但猜错了必须能被兜住——这是 AI 产品与玩具的分水岭。</p>
    </div>
    <div class="cards" style="margin-top:56px;grid-template-columns:repeat(12,1fr)">
      <div class="card" style="grid-column:span 6">
        <div class="cico"><svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M7 8V4a2 2 0 012-2h6a2 2 0 012 2v4M5 8h14v11a2 2 0 01-2 2H7a2 2 0 01-2-2V8z"/></svg></div>
        <span class="cnum">截图询价</span>
        <h4>多模态 OCR</h4>
        <p>客户甩来一张报价截图，VLM 逐字识别仓码与价格，比传统 OCR 更懂表格语义。</p>
      </div>
      <div class="card" style="grid-column:span 6">
        <div class="cico"><svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M9 12l2 2 4-4m5.6-1.6A9 9 0 116.9 4.4"/></svg></div>
        <span class="cnum">白名单兜底</span>
        <h4>防幻觉</h4>
        <p>大模型对形近字符（O/0、I/1、M/N）有随机误差。白名单外的「疑似仓码」不硬报，用编辑距离找相似候选主动确认。</p>
      </div>
      <div class="card" style="grid-column:span 6">
        <div class="cico"><svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M12 3v12m0 0l-4-4m4 4l4-4M4 21h16"/></svg></div>
        <span class="cnum">模型路由</span>
        <h4>大小模型分工</h4>
        <p>普通查价走轻量模型，价表解析走深度模型，图片识别走多模态。成本与效果最优分配。</p>
      </div>
      <div class="card" style="grid-column:span 6">
        <div class="cico"><svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><rect x="3" y="4" width="7" height="16" rx="1"/><rect x="14" y="4" width="7" height="9" rx="1"/></svg></div>
        <span class="cnum">多 Agent</span>
        <h4>协作编排</h4>
        <p>解析入库、询价查询、报价计算、价格监控、数据展示各司其职，单一职责、可独立验证。</p>
      </div>
    </div>
    <div class="tbl-wrap" style="margin-top:56px">
      <table class="tbl">
        <thead><tr><th>能力</th><th>技术</th><th>解决痛点</th></tr></thead>
        <tbody>
          <tr><td>截图询价</td><td>qwen3.8-max（VLM）</td><td>人工抄价慢且易错 → 秒级识别，规则兜底</td></tr>
          <tr><td>模型路由</td><td>deepseek-v4-pro / flash / qwen3.8-max</td><td>一刀切浪费算力 → 按场景最优分配</td></tr>
          <tr><td>智能比价</td><td>渠道母集标准化 + 排序</td><td>渠道名五花八门 → 归集到标准母集再比价</td></tr>
          <tr><td>计费规则引擎</td><td>规则库四维锁定</td><td>附加费漏算就亏钱 → 逐条核，一分不差</td></tr>
          <tr><td>趋势与告警</td><td>SQL 快照对比</td><td>价表周更盯不住涨跌 → 自动对比、异常告警</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</section>
'''

AILAND = '''
<section class="section noise" id="ai-land" style="background:var(--bg-2)">
  <div class="wrap">
    <div class="section-head" style="max-width:720px">
      <span class="eyebrow">AI 应用落地</span>
      <h2 class="h-lg" style="margin-top:20px">把大模型从「能跑通 demo」<br>推到「敢上生产」</h2>
      <p class="lead" style="margin-top:16px">靠的不是更多参数，而是四件事：防幻觉、可验证、可路由、可溯源。</p>
    </div>
    <div class="grid" style="grid-template-columns:1fr 1fr;gap:18px;margin-top:56px">
      <div class="def">
        <span class="dnum">01</span>
        <div><h4>防幻觉三道闸</h4><p>LLM 对形近字符（O/0、I/1、M/N、N/H）有随机误差，绝不让它「猜」仓码。结果先过白名单，白名单外用编辑距离找候选，再主动确认，不硬报。</p></div>
      </div>
      <div class="def">
        <span class="dnum">02</span>
        <div><h4>精度可验证（E==X==D）</h4><p>提取器与真值解析器双路独立解析，逐格对账到源文件；只有 E==X 全绿才放行。版本关系判定：新价表替换旧价表只拦格式错误，同批重验严格对账，旧价表回填新库强阻断。</p></div>
      </div>
      <div class="def">
        <span class="dnum">03</span>
        <div><h4>模型分级路由</h4><p>按任务复杂度与容错等级分配模型：普通查价走轻量模型降本，价表深度解析走强模型保精度，图片识别走多模态。不做一刀切。</p></div>
      </div>
      <div class="def">
        <span class="dnum">04</span>
        <div><h4>可解释可溯源</h4><p>AI 只负责感知与生成，算钱一律走确定性引擎；每条报价可溯源到原始价表与进仓点，引擎只读底价、禁止加价——「宁可不报价，不可报错价」。</p></div>
      </div>
    </div>
  </div>
</section>
'''

# ---------------------------------------------------------------------
RESULT = '''
<section class="section noise" id="result">
  <div class="wrap">
    <div class="grid" style="grid-template-columns:1fr 1.1fr;gap:56px;align-items:start">
      <div>
        <span class="eyebrow">落地成果</span>
        <h2 class="h-lg" style="margin-top:20px">让询价从「分钟级」<br>降到「秒级」</h2>
        <p class="lead" style="margin-top:18px">生产系统实测数据，量化这套系统的落地效果。不是 demo 的天花板，是扛住了真实业务压力的结果。</p>
        <div class="hero-stats" style="margin-top:36px;flex-direction:column;gap:20px">
          <div class="stat"><div class="num" style="font-size:clamp(28px,3vw,40px)"><span data-count="8">8</span>万+</div><div class="lb">条底价沉淀</div></div>
          <div class="stat"><div class="num" style="font-size:clamp(28px,3vw,40px)"><span data-count="600">600</span>+</div><div class="lb">个通达仓码覆盖</div></div>
          <div class="stat"><div class="num" style="font-size:clamp(28px,3vw,40px)"><em>&lt;1</em>秒</div><div class="lb">查询响应</div></div>
        </div>
      </div>
      <div class="tbl-wrap">
        <table class="tbl">
          <thead><tr><th>关键工程决策</th><th>价值</th></tr></thead>
          <tbody>
            <tr><td>三库分离</td><td>生产 / 测试 / 档案物理隔离，测试改动不污染生产，历史可追溯</td></tr>
            <tr><td>分线路分表</td><td>美线 / 欧线 / 加线独立分表，跨线路脏数据从根上杜绝</td></tr>
            <tr><td>原始名保真</td><td>渠道原始名与进仓点保留原文，报价可溯源，不报错价</td></tr>
            <tr><td>底价原则</td><td>引擎只读底价，禁止加价，宁可不报价，不可报错价</td></tr>
            <tr><td>配置集中化</td><td>配置中心单例源头，改一处全局生效，杜绝副本漂移</td></tr>
            <tr><td>全量验证</td><td>提取器输出 vs Excel 源文件逐格比对，覆盖率 100%，数据可信</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</section>
'''

GUARD = '''
<section class="section noise" id="guard" style="background:var(--bg-2)">
  <div class="wrap">
    <div class="section-head" style="max-width:760px">
      <span class="eyebrow">产品责任</span>
      <h2 class="h-lg" style="margin-top:20px">我如何为「报错价」这件事负责</h2>
      <p class="lead" style="margin-top:16px">对一个会真金白银亏钱的产品，我最关心的不是「功能是否炫」，而是「出错了怎么不造成后果」。这六道护栏，每一条都是在替业务兜底——把「少出错」做成机制，把「出错可追溯」做成默认。</p>
    </div>
    <div class="def-lines" style="margin-top:56px">
      <div class="def"><span class="dnum">01</span><div><h4>源头约束</h4><p>非法数据进不来。入库命令参数 + 入库记录结构双重校验，必填字段、类型、合法取值枚举，非法当场拒绝。</p></div></div>
      <div class="def"><span class="dnum">02</span><div><h4>运行中校验</h4><p>异常自动告警。动态基线校验：以历史数据建立滑动窗口，本次数量骤降即告警。有限重试 + 循环检测，防重复入库与死循环。</p></div></div>
      <div class="def"><span class="dnum">03</span><div><h4>风险管控</h4><p>高风险二次确认。任务预拆解、改删生产数据先人工确认、超时熔断降级，防止错误扩散。</p></div></div>
      <div class="def"><span class="dnum">04</span><div><h4>真值对账</h4><p>E==X==D 全量对账。提取器与真值解析器双路独立解析，逐格对账到源文件；版本关系判定：新价表替换旧价表只拦格式错误、同批重验严格对账、旧价表回填新库强阻断。</p></div></div>
      <div class="def"><span class="dnum">05</span><div><h4>生产写保护</h4><p>改生产数据先看影响。写入生产库统一走 dry-run 预览影响行数 + 审计日志 + 人工确认，全链路可审计，改动后留完整回滚基线。</p></div></div>
      <div class="def"><span class="dnum">06</span><div><h4>强不变量扫描</h4><p>合理性扫描兜底。以强不变量做合理性扫描（计费重、单位匹配等），异常数超上限才告警；默认维持零打扰的 info 级，异常明细进巡检报告供人工复核。</p></div></div>
    </div>
  </div>
</section>
'''

OUTRO = '''
<section class="section noise outro" id="outro">
  <div class="wrap">
    <span class="eyebrow" style="justify-content:center;display:flex">关于这个项目</span>
    <h2 class="h-lg" style="margin-top:22px">把 AI 真正落到业务，<br>是产品人最值钱的能力</h2>
    <p class="lead" style="max-width:620px;margin:22px auto 0">这个项目里，我完成的不是「调用一个 API」，而是一个完整的产品闭环：理解业务 → 判断该不该用 AI → 拆解落地 → 验证结果。</p>
    <div class="steps">
      <div class="step"><span class="sn">先 · 理解</span><h4>业务理解</h4><p>不坐在办公室臆想需求，而是走到业务现场，看商务怎么翻表、怎么算价、错在哪里。</p></div>
      <div class="step"><span class="sn">再 · 判断</span><h4>AI 判断</h4><p>清楚知道大模型的强项与命门——用于容错，不用于负责。这是 AI 产品落地最核心的判断。</p></div>
      <div class="step"><span class="sn">后 · 落地</span><h4>落地能力</h4><p>不满足于 demo，把「准确率」「可溯源」「可回滚」做成一等公民，敢上生产、敢负责任。</p></div>
    </div>
  </div>
</section>
'''

FOOT = '''
<footer class="foot">
  <div class="wrap">
    <span>FreightGo · 跨境商务智能询报价系统</span>
    <span style="font-family:var(--mono);letter-spacing:.04em">Made with product judgment</span>
  </div>
</footer>
'''

# ---------------------------------------------------------------------
# GSAP ScrollTrigger scroll-driven engine + Canvas particles
scroll_js = r'''
/* ===== V3 scroll-driven engine (GSAP ScrollTrigger) ===== */
var HAS_GSAP = (typeof gsap !== 'undefined') && (typeof ScrollTrigger !== 'undefined');
function onReady(fn){ if(document.readyState!='loading') fn(); else document.addEventListener('DOMContentLoaded', fn); }

onReady(function(){
  // ---- 0. Fallback reveal polyfill (if GSAP missing) ----
  function softReveal(){
    var els = document.querySelectorAll('.rv,.card,.def,.layer,.tl-card');
    if(HAS_GSAP) return;
    var io = new IntersectionObserver(function(es){
      es.forEach(function(e){ if(e.isIntersecting){ e.target.style.opacity=1; e.target.style.transform='none'; io.unobserve(e.target);} });
    }, {threshold:.1});
    els.forEach(function(el){ el.style.opacity=.55; el.style.transform='translateY(26px)'; io.observe(el); });
  }
  softReveal();

  // ---- 1. Nav + progress ----
  var nav = document.getElementById('nav');
  var progress = document.getElementById('progress');
  function onScrollUI(){
    if(nav) nav.classList.toggle('scrolled', window.scrollY > 40);
    if(progress){
      var h = document.documentElement.scrollHeight - window.innerHeight;
      progress.style.width = (h>0 ? (window.scrollY/h*100) : 0) + '%';
    }
  }
  window.addEventListener('scroll', onScrollUI, {passive:true});
  onScrollUI();

  // ---- 2. Hero title word-by-word light-up (scrub) — delivery-safe: never hidden ----
  var heroTitle = document.getElementById('hero-title');
  if(heroTitle && HAS_GSAP){
    // split each .line into words
    var words = [];
    heroTitle.querySelectorAll('.line').forEach(function(line){
      var text = line.textContent;
      line.textContent = '';
      text.split(/(\s+)/).forEach(function(seg){
        if(!seg) return;
        if(/^\s+$/.test(seg)){ line.appendChild(document.createTextNode(' ')); return; }
        var s = document.createElement('span'); s.className='w'; s.textContent=seg; line.appendChild(s); words.push(s);
      });
    });
    // words always fully readable (opacity 1); scrub drives a subtle rise + color pop, never opacity fade
    gsap.set('#'+heroTitle.id+' .w', {opacity:1, y:0});
    gsap.fromTo('#'+heroTitle.id+' .w',
      { y:26, opacity:1 },
      { y:0, opacity:1, stagger:.06, ease:'none',
        scrollTrigger:{ trigger:'#top', start:'top top', end:'60% top', scrub:.6 }
      }
    );
  }

  // ---- 3. Duel parallax + reveal — delivery-safe: never hidden, only rise ----
  if(HAS_GSAP){
    gsap.utils.toArray('.duel-card').forEach(function(card, i){
      gsap.fromTo(card, {y:50, opacity:.55}, {
        y:0, opacity:1, duration:1.1, ease:'power3.out',
        scrollTrigger:{ trigger:card, start:'top 90%', end:'top 45%', scrub:.4 }
      });
    });
    gsap.fromTo('.section-head', {y:40, opacity:.5}, {
      y:0, opacity:1, duration:1, ease:'power3.out',
      scrollTrigger:{ trigger:'.section-head', start:'top 88%', end:'top 50%', scrub:.5 }
    });
  }

  // ---- 4. (removed) Scroll-track timeline pin+horizontal — flow now plain vertical, no crazy scroll ----

  // ---- 5. Generic reveal scrub — delivery-safe: never hidden ----
  if(HAS_GSAP){
    gsap.utils.toArray('.card').forEach(function(el){
      gsap.fromTo(el, {y:44, opacity:.5}, {
        y:0, opacity:1, duration:.9, ease:'power3.out',
        scrollTrigger:{ trigger:el, start:'top 92%', end:'top 55%', scrub:.4 }
      });
    });
    gsap.utils.toArray('.def,.layer').forEach(function(el){
      gsap.fromTo(el, {y:36, opacity:.5}, {
        y:0, opacity:1, duration:.9, ease:'power3.out',
        scrollTrigger:{ trigger:el, start:'top 94%', end:'top 60%', scrub:.4 }
      });
    });
  }

  // ---- 6. Count-up numbers — static final now (delivery-safe); light animate on enter ----
  function showFinal(el){
    var t = parseFloat(el.getAttribute('data-count'));
    el.textContent = isNaN(t)? '0' : t.toLocaleString('en-US');
  }
  document.querySelectorAll('[data-count]').forEach(showFinal); // render final immediately
  // optional short count-up when a .stat enters viewport (starts from final, quick)
  var countIO = new IntersectionObserver(function(es){
    es.forEach(function(e){
      if(e.isIntersecting){
        e.target.querySelectorAll('[data-count]').forEach(function(el){
          el.setAttribute('data-played','1');
          var target = parseFloat(el.getAttribute('data-count'));
          var start = target, dur=450, t0=performance.now();
          function tick(now){
            var p = Math.min((now-t0)/dur,1);
            var val = Math.round(target*(1-p) + target*p); // start=target -> stays target (no dip)
            el.textContent = val.toLocaleString('en-US');
            if(p<1) requestAnimationFrame(tick); else showFinal(el);
          }
          requestAnimationFrame(tick);
        });
        countIO.unobserve(e.target);
      }
    });
  },{threshold:.4});
  document.querySelectorAll('.hero-stats .stat,#result .stat').forEach(function(s){ countIO.observe(s); });

  // ---- 7. Canvas particle field background (hero) ----
  var canvas = document.getElementById('hero-canvas');
  if(canvas){
    var ctx = canvas.getContext('2d');
    var W,H,parts=[],mouse={x:-999,y:-999};
    var COL = {'13,148,136':true,'8,145,178':true,'14,165,233':false};
    function resize(){
      W = canvas.width = canvas.offsetWidth;
      H = canvas.height = canvas.offsetHeight;
      init();
    }
    function init(){
      parts = [];
      var n = Math.min(110, Math.floor(W*H/16000));
      for(var i=0;i<n;i++){
        var c = i%9===0 ? 'rgba(13,148,136,AL)' : (i%11===0? 'rgba(8,145,178,AL)' : 'rgba(14,165,233,AL)');
        parts.push({x:Math.random()*W, y:Math.random()*H, r:Math.random()*1.6+.4, vx:(Math.random()-.5)*.3, vy:(Math.random()-.5)*.3, c:c});
      }
    }
    function draw(){
      ctx.clearRect(0,0,W,H);
      for(var i=0;i<parts.length;i++){
        var p = parts[i];
        p.x+=p.vx; p.y+=p.vy;
        if(p.x<0||p.x>W) p.vx*=-1;
        if(p.y<0||p.y>H) p.vy*=-1;
        // gentle mouse attraction
        var dx=mouse.x-p.x, dy=mouse.y-p.y, d=Math.sqrt(dx*dx+dy*dy);
        if(d<140){ p.x+=dx/d*0.6; p.y+=dy/d*0.6; }
        var alpha = p.c.indexOf('13,148,136')>=0? .42 : (p.c.indexOf('8,145,178')>=0? .34 : .16);
        ctx.fillStyle = p.c.replace('AL', alpha);
        ctx.beginPath(); ctx.arc(p.x,p.y,p.r,0,6.283); ctx.fill();
      }
      // connect nearby
      for(var a=0;a<parts.length;a++){
        for(var b=a+1;b<parts.length;b++){
          var dx2=parts[a].x-parts[b].x, dy2=parts[a].y-parts[b].y, d2=Math.sqrt(dx2*dx2+dy2*dy2);
          if(d2<110){
            ctx.strokeStyle='rgba(13,148,136,'+(0.04*(1-d2/110))+')';
            ctx.lineWidth=1; ctx.beginPath(); ctx.moveTo(parts[a].x,parts[a].y); ctx.lineTo(parts[b].x,parts[b].y); ctx.stroke();
          }
        }
      }
      requestAnimationFrame(draw);
    }
    window.addEventListener('resize', resize);
    window.addEventListener('mousemove', function(e){ mouse.x=e.clientX; mouse.y=e.clientY; });
    resize(); draw();
  }
});

// Re-register ScrollTrigger refresh after images/fonts
window.addEventListener('load', function(){ if(HAS_GSAP && ScrollTrigger) ScrollTrigger.refresh(); });
'''

# ---------------------------------------------------------------------
if __name__ == '__main__':
    # assemble — all narrative sections + live product demo + engines
    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="FreightGo · 跨境商务智能询报价系统 — 把一个真实业务痛点做成能上生产的产品。">
<title>FreightGo · 跨境商务智能询报价系统</title>
<link rel="preconnect" href="https://cdn.jsdelivr.net">
<style>
%s
</style>
<style>
%s
</style>
</head>
<body>
<div class="glow-bg"><span class="g1"></span><span class="g2"></span><span class="g3"></span></div>
%s
%s
%s
<script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/ScrollTrigger.min.js"></script>
<script>
%s
</script>
<script>
%s
</script>
<script>
%s
</script>
</body>
</html>""" % (styles_v3, demo_css, NAV, HERO, "\n".join([DUEL, PROBLEM, APPROACH, FLOW, PRODUCT_AREA, ARCH, AI, AILAND, RESULT, GUARD, OUTRO, FOOT]), scroll_js, tab_js, inject_js)

    out = os.path.join(HERE, 'index.html')
    with io.open(out, 'w', encoding='utf-8') as f:
        f.write(html)
    print('built', out, 'len', len(html))
