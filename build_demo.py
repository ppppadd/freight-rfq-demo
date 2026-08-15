#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
演示版询报价网页生成脚本（面试展示用）

用途：生成一个【脱敏 + 虚拟数据】的询报价系统演示网页，证明项目可行性与落地性。

特点：
  1. 数据全部为虚拟编撰（非任何真实供应商价格），结构对齐真实系统；
  2. 移除网页内所有真实公司/供应商名称；
  3. 复用真实系统的 single.html 模板与渲染逻辑，保证界面与交互一致；
  4. 输出单文件 index.html，双击即可打开演示。

用法：
  python3 build_demo.py [--template 模板路径] [--output 输出文件]

依赖（仅趋势图模块，缺失时自动降级）：
  skills/supplier-data-show/modules/web-builder/trend_inject.py 的 _render_html
"""
import argparse
import json
import os
import random
import re
import sys
from datetime import datetime, timedelta

# ============================================================
# 一、虚拟业务对象定义（全部为编撰数据，非真实）
# ============================================================

# 虚拟平台名（脱敏：替换真实品牌）
PLATFORM_NAME = "FreightGo"
PLATFORM_TAGLINE = "跨境物流智能询价平台"

# 虚拟供应商（8 家，代号 + 虚拟名称）
SUPPLIERS = [
    ("S1", "启航物流"),
    ("S2", "远洋供应链"),
    ("S3", "云帆国际"),
    ("S4", "星辰速运"),
    ("S5", "蓝海物流"),
    ("S6", "宏图跨境"),
    ("S7", "顺达集运"),
    ("S8", "通达国际"),
]

# 美线卡派渠道（母集标准大类）
US_CARD_CHANNELS = [
    "美森CLX正班", "美森MAX加班", "合德ZIM快提", "合德ZIM普提",
    "普船卡派", "普船特惠卡派", "纽约卡派", "萨凡纳卡派",
    "芝加哥卡派", "休斯顿卡派",
]

# 美线海派渠道
US_HAIPAI_CHANNELS = [
    "美森CLX正班海派", "美森MAX加班海派", "合德ZIM快提海派",
    "合德ZIM普提海派", "普船海派", "普船特惠海派",
]

# 欧线渠道
EU_CHANNELS = [
    "欧洲卡航DDP", "欧洲卡航DDU", "欧洲海运DDP", "欧洲海运DDU",
    "欧洲铁路DDP", "欧洲铁路DDU", "英国卡航DDP", "英国海运DDP",
    "英国铁路DDP", "欧洲空运DDP",
]

# 美线 FBA 仓库代码（亚马逊公开仓码，非公司机密）
US_WAREHOUSES = [
    "ONT8", "LGB8", "LAX9", "SBD1", "SMF3", "GYR3", "PHX7",
    "FTW1", "DFW6", "SAT1", "MEM1", "BNA2", "IND9", "CVG2",
    "CMH3", "ORD2", "MDW2", "MKE1", "ATL2", "CLT2", "ABE8",
    "EWR4", "BWI2", "JFK8", "HOU8", "TPA1", "MIA1", "DEN4",
    "SLC1", "SEA6",
]

# 欧洲仓库代码（亚马逊欧洲公开仓码）
EU_WAREHOUSES = [
    "DTM2", "WRO5", "BER8", "CDG7", "HAJ1", "DUS2", "XUKS",
    "BHX4", "MAN1", "STN8", "LPL2", "POZ1", "FRA3", "MUC3", "CGN2",
]

# 进仓点（华东/华南主要集货地）
INBOUND_POINTS = ["义乌", "深圳", "宁波", "上海", "青岛", "厦门"]

# 卡派渠道基价（51KG+，元/KG）与时效（天）——虚拟值
CHANNEL_BASE = {
    "美森CLX正班": (11.0, (10, 12)),
    "美森MAX加班": (10.5, (11, 13)),
    "合德ZIM快提": (9.0, (12, 15)),
    "合德ZIM普提": (8.5, (15, 18)),
    "普船卡派": (6.5, (22, 28)),
    "普船特惠卡派": (6.0, (24, 30)),
    "纽约卡派": (7.5, (25, 32)),
    "萨凡纳卡派": (7.8, (26, 33)),
    "芝加哥卡派": (7.2, (24, 31)),
    "休斯顿卡派": (7.5, (25, 32)),
}

# 重量段折扣系数（相对 51KG+ 基准）
WEIGHT_FACTOR = {12: 1.15, 51: 1.0, 100: 0.92}
HAIPAI_WEIGHT_FACTOR = {12: 1.18, 51: 1.0, 101: 0.90}

# 海派渠道基价（元/KG）
HAIPAI_BASE = {
    "美森CLX正班海派": 22.0, "美森MAX加班海派": 21.0,
    "合德ZIM快提海派": 19.0, "合德ZIM普提海派": 18.0,
    "普船海派": 16.0, "普船特惠海派": 15.0,
}

# 欧线渠道基价（元/KG）
EU_BASE = {
    "欧洲卡航DDP": 16.0, "欧洲卡航DDU": 15.0,
    "欧洲海运DDP": 11.0, "欧洲海运DDU": 10.0,
    "欧洲铁路DDP": 12.0, "欧洲铁路DDU": 11.0,
    "英国卡航DDP": 17.0, "英国海运DDP": 12.0,
    "英国铁路DDP": 13.0, "欧洲空运DDP": 28.0,
}

# 周报类型（对应前端 6 张卡片）
WEEKLY_TYPES = ["运价走势", "WCI", "本周概览", "最优报价", "市场预测", "重点关注"]

random.seed(20260815)  # 固定种子，保证每次生成结果可复现


# ============================================================
# 二、虚拟数据生成
# ============================================================

def _jitter(base, pct=0.05):
    """在基价基础上做 ±pct 的确定性扰动，模拟供应商竞争差异"""
    return round(base * (1 + random.uniform(-pct, pct)), 2)


def generate_us_data():
    """生成美线卡派数据（per_kg）"""
    data = []
    for wh in US_WAREHOUSES:
        # 每个仓随机 5~7 家供应商
        sups = random.sample(SUPPLIERS, random.randint(5, 7))
        for code, name in sups:
            # 每家供应商随机 3~5 个渠道
            chs = random.sample(US_CARD_CHANNELS, random.randint(3, 5))
            for ch in chs:
                base, (tlo, thi) = CHANNEL_BASE[ch]
                inbound = random.choice(INBOUND_POINTS[:3])  # 华东/华南
                for wt, factor in WEIGHT_FACTOR.items():
                    price = round(base * factor * (1 + random.uniform(-0.05, 0.05)), 2)
                    data.append({
                        "w": wh, "s": name, "c": ch, "wt": wt,
                        "p": price, "u": "per_kg", "dd": "DDP",
                        "inbound": inbound,
                        "t_min": tlo + random.randint(0, 2),
                        "t_max": thi + random.randint(0, 3),
                    })
    return data


def generate_us_cbm_data():
    """生成美线卡派 CBM 数据（per_cbm）"""
    data = []
    for wh in random.sample(US_WAREHOUSES, 18):
        sups = random.sample(SUPPLIERS, random.randint(2, 4))
        for code, name in sups:
            chs = random.sample(US_CARD_CHANNELS, random.randint(1, 2))
            for ch in chs:
                base, (tlo, thi) = CHANNEL_BASE[ch]
                for cbm in (1, 2, 3):
                    # 1CBM ≈ 363KG，方价约 = KG 价 × 363 的低消折合（虚拟值）
                    price = round(base * 300 * (1 + random.uniform(-0.08, 0.08)), 0)
                    data.append({
                        "w": wh, "s": name, "c": ch, "wt": cbm,
                        "p": price, "u": "per_cbm", "dd": "DDP",
                        "inbound": random.choice(INBOUND_POINTS[:3]),
                        "t_min": tlo, "t_max": thi,
                    })
    return data


def generate_us_haipai_data():
    """生成美线海派数据"""
    data = []
    for wh in US_WAREHOUSES:
        sups = random.sample(SUPPLIERS, random.randint(3, 5))
        for code, name in sups:
            chs = random.sample(US_HAIPAI_CHANNELS, random.randint(2, 3))
            for ch in chs:
                base = HAIPAI_BASE[ch]
                for wt, factor in HAIPAI_WEIGHT_FACTOR.items():
                    price = round(base * factor * (1 + random.uniform(-0.05, 0.05)), 2)
                    data.append({
                        "w": wh, "s": name, "c": ch, "wt": wt,
                        "p": price, "u": "per_kg", "dd": "DDP",
                        "inbound": random.choice(INBOUND_POINTS[:3]),
                        "t_min": 9 + random.randint(0, 3),
                        "t_max": 13 + random.randint(0, 4),
                    })
    return data


def generate_eu_data():
    """生成欧线数据"""
    data = []
    for wh in EU_WAREHOUSES:
        sups = random.sample(SUPPLIERS, random.randint(3, 5))
        for code, name in sups:
            chs = random.sample(EU_CHANNELS, random.randint(3, 5))
            for ch in chs:
                base = EU_BASE[ch]
                is_air = "空运" in ch
                for wt, factor in ((21, 1.1), (51, 1.0), (101, 0.92)):
                    price = round(base * factor * (1 + random.uniform(-0.06, 0.06)), 2)
                    t = (5, 7) if is_air else (random.randint(25, 30), random.randint(32, 40))
                    data.append({
                        "w": wh, "s": name, "c": ch, "wt": wt,
                        "p": price, "u": "per_kg", "dd": ch[-3:],
                        "inbound": random.choice(INBOUND_POINTS),
                        "t_min": t[0], "t_max": t[1],
                    })
    return data


def build_site_data():
    """组装完整的 site_data（对齐真实系统 build.py 的字段）"""
    us_data = generate_us_data()
    us_cbm_data = generate_us_cbm_data()
    us_haipai_data = generate_us_haipai_data()
    eu_data = generate_eu_data()

    # 仓库列表
    warehouses = sorted(US_WAREHOUSES)

    # 供应商统计
    supplier_stats = {}
    for code, name in SUPPLIERS:
        recs = [d for d in us_data if d["s"] == name]
        whs = {d["w"] for d in recs}
        supplier_stats[code] = {
            "name": name, "warehouses": len(whs), "records": len(recs),
        }

    # 渠道列表
    channels = US_CARD_CHANNELS
    haipai_channels = US_HAIPAI_CHANNELS
    eu_channels = EU_CHANNELS

    # 热门仓价格（选前 8 个仓，每仓取最低价）
    hot_prices = []
    for wh in US_WAREHOUSES[:8]:
        rows = [d for d in us_data if d["w"] == wh and d["wt"] >= 51]
        rows.sort(key=lambda x: x["p"])
        if rows:
            top = rows[:3]
            hot_prices.append({
                "warehouse": wh, "tag": "热门",
                "lowest_price": top[0]["p"], "supplier": top[0]["s"],
                "channel": top[0]["c"], "t_min": top[0]["t_min"], "t_max": top[0]["t_max"],
                "all_prices": [
                    {"supplier": r["s"], "price": r["p"], "channel": r["c"],
                     "t_min": r["t_min"], "t_max": r["t_max"]}
                    for r in top
                ],
            })

    # 渠道排名（每渠道按最低价排供应商）
    channel_rankings = []
    for ch in US_CARD_CHANNELS:
        rows = [d for d in us_data if d["c"] == ch and d["wt"] >= 12]
        by_sup = {}
        for r in rows:
            if r["s"] not in by_sup or r["p"] < by_sup[r["s"]]["price"]:
                by_sup[r["s"]] = {"supplier": r["s"], "price": r["p"],
                                  "t_min": r["t_min"], "t_max": r["t_max"]}
        sups = sorted(by_sup.values(), key=lambda x: x["price"])
        if sups:
            for s in sups:
                s["code"] = [c for c, n in SUPPLIERS if n == s["supplier"]][0]
            channel_rankings.append({"channel": ch, "suppliers": sups})

    # 周报（虚拟）
    now = datetime.now()
    week_of = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
    weekly_news = {
        "week_of": week_of,
        "news": [
            {"type": "运价走势", "title": "美线运价本周小幅回落",
             "summary": "SCFI 综合指数环比 -2.3%，美西航线领跌，普船卡派均价下探至 6.5 元/KG 附近。",
             "source": "演示数据", "date": week_of, "link": "#query"},
            {"type": "WCI", "title": "全球集装箱运价指数 WCI",
             "summary": "WCI 本周报 4,120 美元/FEU，较上周 -1.8%，跨太平洋航线降幅最为明显。",
             "source": "演示数据", "date": week_of, "link": "#"},
            {"type": "本周概览", "title": "本周 8 家供应商 · 10 条渠道",
             "summary": "共覆盖 30 个 FBA 仓库，合计 1,500+ 条有效报价，美森/合德/普船全线可查。",
             "source": "演示数据", "date": week_of, "link": "#channels"},
            {"type": "最优报价", "title": "普船特惠卡派本周最低 5.82 元/KG",
             "summary": "普船特惠卡派在华东进仓、51KG+ 档位下探至最低价，适合大批量补货。",
             "source": "演示数据", "date": week_of, "link": "#query"},
            {"type": "市场预测", "title": "Q3 旺季临近，运价或温和上行",
             "summary": "Q3 传统旺季叠加航线运力收紧，预计下周运价止跌企稳，建议提前锁价。",
             "source": "演示数据", "date": week_of, "link": "#"},
            {"type": "重点关注", "title": "美森 CLX 正班时效领跑",
             "summary": "美森 CLX 正班开船后 10-12 天入仓，时效最优，适合高周转 SKU 补货。",
             "source": "演示数据", "date": week_of, "link": "#"},
        ],
        "next_update": "下周一 09:00 自动更新",
    }

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "warehouses": warehouses,
        "supplier_stats": supplier_stats,
        "channels": channels,
        "haipai_channels": haipai_channels,
        "eu_channels": eu_channels,
        "hot_prices": hot_prices,
        "channel_rankings": channel_rankings,
        "us_data": us_data,
        "us_cbm_data": us_cbm_data,
        "us_haipai_data": us_haipai_data,
        "eu_data": eu_data,
        "weekly_news": weekly_news,
    }


# ============================================================
# 三、趋势图（虚拟 4 周价格走势）
# ============================================================

def _try_import_trend_renderer():
    """优先复用真实系统的趋势图渲染器，失败返回 None"""
    try:
        build_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "skills", "supplier-data-show", "modules", "web-builder")
        if build_dir not in sys.path:
            sys.path.insert(0, build_dir)
        from trend_inject import _render_html
        return _render_html
    except Exception:
        return None


def build_trend_configs():
    """构造 6 个渠道、近 4 周的虚拟价格走势（chart_configs）"""
    colors = ["#E74C3C", "#3498DB", "#2ECC71", "#F39C12", "#9B59B6", "#1ABC9C"]
    weeks = []
    today = datetime.now()
    for i in range(3, -1, -1):
        d = today - timedelta(weeks=i) - timedelta(days=today.weekday())
        weeks.append(d.strftime("%m-%d"))

    cfgs = []
    for ci, ch in enumerate(US_CARD_CHANNELS[:6]):
        base, _ = CHANNEL_BASE[ch]
        datasets = []
        # 选 3 家供应商参与趋势
        for si, (code, name) in enumerate(SUPPLIERS[:3]):
            # 每家一条略不同的走势线
            data = [round(base * (1 + 0.05 * (si - 1) + 0.03 * (wi - 1.5) + random.uniform(-0.02, 0.02)), 2)
                    for wi in range(4)]
            datasets.append({
                "label": name, "data": data,
                "borderColor": colors[si % len(colors)],
                "borderWidth": 2.5, "pointRadius": 5,
                "pointHoverRadius": 7, "tension": 0.25,
                "fill": False, "spanGaps": True,
            })
        all_rates = [r for ds in datasets for r in ds["data"]]
        lo, hi = min(all_rates), max(all_rates)
        span = hi - lo
        # 走势概括
        first, last = datasets[0]["data"][0], datasets[0]["data"][-1]
        word = "下行" if last < first else "上行"
        summary = f"整体{word}。{datasets[0]['label']}从 {first:.1f} 走至 {last:.1f} 元/KG（{'+' if last>=first else ''}{(last/first-1)*100:.1f}%）。"
        cfgs.append({
            "channel": ch, "chartId": f"demo_{ci}",
            "labels": weeks, "datasets": datasets,
            "supplierCount": len(datasets),
            "yRange": {"min": round(lo - span * 0.15 - 0.1, 1), "max": round(hi + span * 0.15 + 0.1, 1)},
            "summary": summary,
        })
    return cfgs


def build_trend_html():
    """生成趋势图 HTML，缺失渲染器时降级为空占位"""
    renderer = _try_import_trend_renderer()
    if renderer is None:
        return ('<section class="sec trend-sec fade-in">'
                '<div class="sec-label dark">Trends</div>'
                '<div class="sec-title dark">6大渠道价格趋势</div>'
                '<p style="color:#999;text-align:center;padding:40px">'
                '趋势图模块未加载（演示环境降级展示）</p></section>')
    return renderer(build_trend_configs())


# ============================================================
# 四、脱敏 + 渲染（复用真实系统 render_single_page 逻辑）
# ============================================================

def _extract_array_bounds(html, var_name):
    """找到 var VARNAME = [ ... ]; 的起止索引"""
    start_marker = f"var {var_name} = ["
    idx = html.find(start_marker)
    if idx == -1:
        return None, None
    bracket_start = idx + len(start_marker) - 1
    depth = 0
    i = bracket_start
    while i < len(html):
        ch = html[i]
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                semi = html.find(";", i + 1)
                return idx, semi + 1 if semi != -1 else i + 1
        i += 1
    return idx, i


def _generate_hot_prices_html(hot_prices):
    if not hot_prices:
        return '<div class="hs-item" style="cursor:default"><span class="hs-item-sub">暂无数据</span></div>'
    items = []
    for hp in hot_prices:
        transit = f'{hp.get("t_min")}-{hp.get("t_max")}天' if hp.get("t_min") and hp.get("t_max") else ""
        parts = [hp.get("channel", ""), hp.get("supplier", "")]
        if transit:
            parts.append(transit)
        sub = " · ".join([p for p in parts if p])
        wh = hp.get("warehouse", "")
        price = hp.get("lowest_price")
        price_str = f"¥{price:.1f}" if price is not None else "—"
        items.append(
            f'<div class="hs-item" data-wh="{wh}" onclick="showQueryPage(\'{wh}\')">'
            f'<span class="hs-item-wh">{wh}</span>'
            f'<span class="hs-item-sub">{sub}</span>'
            f'<span class="hs-item-val">{price_str}</span></div>')
    return "\n".join(items)


def _generate_channel_ranking_cards(channel_rankings):
    if not channel_rankings:
        return ""
    medals = ["🥇", "🥈", "🥉"]
    cards = []
    for i, item in enumerate(channel_rankings):
        channel = item["channel"]
        suppliers = item["suppliers"]
        supplier_items = []
        for j, sup in enumerate(suppliers[:3]):
            price_str = f"¥{sup['price']:.1f}"
            transit = f"{sup['t_min']}-{sup['t_max']}天" if sup.get("t_min") and sup.get("t_max") else ""
            transit_html = f' <span class="rk-transit">{transit}</span>' if transit else ""
            supplier_items.append(
                f'<div class="rk-item">{medals[j]} {sup["supplier"]} '
                f'<span class="rk-price">{price_str}</span>{transit_html}</div>')
        card_html = (
            f'<div class="rk-card fade-in-card" style="animation-delay:{i*0.06:.2f}s" '
            f'data-channel="{channel}" onclick="expandRanking(this)">'
            f'<div class="rk-channel">{channel}</div>'
            f'<div class="rk-suppliers">{"".join(supplier_items)}</div></div>')
        cards.append(card_html)
    return "\n".join(cards)


def _generate_weekly_news_html(weekly_news):
    news_list = weekly_news.get("news", [])
    if not news_list:
        return "", ""
    type_styles = {
        "运价走势": ("tg-t", "var(--ac)"),
        "WCI": ("tg-d", "var(--gn)"),
        "本周概览": ("tg-r", "var(--ac)"),
        "最优报价": ("tg-d", "var(--gn)"),
        "市场预测": ("tg-o", "#f97316"),
        "重点关注": ("tg-c", "#ef4444"),
    }
    cards = []
    for item in news_list:
        ntype = item.get("type", "")
        tag_cls, bar_color = type_styles.get(ntype, ("tg-d", "var(--ac)"))
        link = item.get("link", "#")
        onclick = "return false"
        if link == "#query":
            onclick = "showQueryPage(''); return false"
        elif link == "#channels":
            onclick = "document.getElementById('channels')&&document.getElementById('channels').scrollIntoView({behavior:'smooth'}); return false"
        card = (
            f'<div class="rc"><div class="rc-bar" style="background:{bar_color}"></div>'
            f'<a href="#" onclick="{onclick}"><div class="rc-body">'
            f'<span class="rc-tag {tag_cls}">{ntype}</span>'
            f'<h3>{item.get("title","")}</h3><p>{item.get("summary","")}</p>'
            f'<div class="rc-meta">{item.get("source","")} · {item.get("date","")}</div>'
            f'</div></a></div>')
        cards.append(card)
    news_html = "\n".join(cards)

    week_of = weekly_news.get("week_of", "")
    week_desc = ""
    if week_of:
        try:
            d = datetime.strptime(week_of, "%Y-%m-%d")
            iso = d.isocalendar()
            week_desc = f"{d.year} 年第 {iso[1]} 周 · {d.strftime('%m.%d')}"
        except Exception:
            week_desc = ""
    return news_html, week_desc


def render(site_data, template_html, output_path):
    """将虚拟数据注入脱敏后的模板，生成单文件 demo 网页"""
    html = template_html

    us_data_json = json.dumps(site_data.get("us_data", []), ensure_ascii=False)
    us_cbm_json = json.dumps(site_data.get("us_cbm_data", []), ensure_ascii=False)
    us_haipai_json = json.dumps(site_data.get("us_haipai_data", []), ensure_ascii=False)
    eu_data_json = json.dumps(site_data.get("eu_data", []), ensure_ascii=False)
    warehouses_json = json.dumps(site_data.get("warehouses", []), ensure_ascii=False)
    channels_json = json.dumps(site_data.get("channels", []), ensure_ascii=False)
    haipai_json = json.dumps(site_data.get("haipai_channels", []), ensure_ascii=False)
    generated_at = site_data.get("generated_at", "")

    for var_name, json_str in [
        ("US_DATA", us_data_json), ("US_CBM_DATA", us_cbm_json),
        ("US_HAIPAI_DATA", us_haipai_json), ("EU_DATA", eu_data_json),
        ("WAREHOUSES", warehouses_json), ("CHANNELS", channels_json),
    ]:
        start, end = _extract_array_bounds(html, var_name)
        if start is not None and end is not None:
            html = html[:start] + f"var {var_name} = {json_str};" + html[end:]

    if "var HAIPAI_CHANNELS" not in html:
        pos = html.find("var CHANNELS = ")
        if pos != -1:
            semi = html.find(";", pos)
            if semi != -1:
                html = html[:semi + 1] + f"\nvar HAIPAI_CHANNELS = {haipai_json};" + html[semi + 1:]

    generated_at_date = generated_at[:10]

    wh_count = len(site_data.get("warehouses", []))
    sup_count = len(site_data.get("supplier_stats", {}))
    ch_count = len(site_data.get("channels", []))
    price_count = (len(site_data.get("us_data", [])) + len(site_data.get("us_cbm_data", []))
                   + len(site_data.get("us_haipai_data", [])))

    html = html.replace('<span id="statSup">13</span>', f'<span id="statSup">{sup_count}</span>')
    html = html.replace('<span id="statSup2">13</span>', f'<span id="statSup2">{sup_count}</span>')
    html = html.replace('<span id="statWh">307</span>', f'<span id="statWh">{wh_count:,}</span>')
    html = html.replace('<span id="statWh2">307</span>', f'<span id="statWh2">{wh_count:,}</span>')
    html = html.replace('<span id="priceCount">50000</span>', f'<span id="priceCount">{price_count:,}</span>')
    html = re.sub(r"数据更新 [\d.]+", f"数据更新 {generated_at}", html)

    html = html.replace("<!-- CHANNEL_RANKING_CARDS -->",
                        _generate_channel_ranking_cards(site_data.get("channel_rankings", [])))
    html = html.replace("<!-- RANKING_DATA_JS -->",
                        f"var GENERATED_AT = \"{generated_at_date}\";\nvar RANKING_DATA = "
                        + json.dumps(site_data.get("channel_rankings", []), ensure_ascii=False) + ";")

    news_html, week_desc = _generate_weekly_news_html(site_data.get("weekly_news", {}))
    html = html.replace("<!-- 周报内容将通过build.py动态生成 -->", news_html)

    html = html.replace("<!-- HOT_PRICES -->", _generate_hot_prices_html(site_data.get("hot_prices", [])))
    html = html.replace("<!-- TREND_CHARTS -->", site_data.get("trend_html", ""))

    if week_desc:
        html = re.sub(r'<div class="sec-desc dark" id="weeklyDesc">[^<]*</div>',
                      f'<div class="sec-desc dark" id="weeklyDesc">{week_desc}</div>', html)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return output_path


def desensitize(html):
    """脱敏：移除真实公司/供应商名称"""
    html = html.replace("保宏境通", PLATFORM_NAME)
    html = html.replace("跨境物流价格平台", PLATFORM_TAGLINE)

    # 替换供应商映射对象（模板内 SUPPLIER_NAMES）
    sup_map = {code: name for code, name in SUPPLIERS}
    sup_js = json.dumps(sup_map, ensure_ascii=False)
    html = re.sub(r"var SUPPLIER_NAMES = \{[^}]*\};", f"var SUPPLIER_NAMES = {sup_js};", html)
    return html


def _find_template():
    """向上查找开发环境中的 single.html 模板"""
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "skills", "supplier-data-show", "modules", "web-builder", "templates", "single.html"),
        os.path.join(here, "..", "skills", "supplier-data-show", "modules", "web-builder", "templates", "single.html"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return candidates[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", default=_find_template())
    ap.add_argument("--output", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "index.html"))
    args = ap.parse_args()

    print("📄 读取模板...")
    with open(args.template, encoding="utf-8") as f:
        html = f.read()

    print("🧹 脱敏处理（移除真实公司名称）...")
    html = desensitize(html)

    print("📊 生成虚拟数据...")
    site_data = build_site_data()

    print("📈 生成趋势图...")
    site_data["trend_html"] = build_trend_html()

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    print("🖥️  渲染演示网页...")
    render(site_data, html, args.output)

    print(f"✅ 完成：{args.output}")
    print(f"   数据规模：卡派 {len(site_data['us_data'])} 条 | CBM {len(site_data['us_cbm_data'])} 条 "
          f"| 海派 {len(site_data['us_haipai_data'])} 条 | 欧线 {len(site_data['eu_data'])} 条")
    print(f"   供应商 {len(SUPPLIERS)} 家 · 仓库 {len(site_data['warehouses'])} 个")


if __name__ == "__main__":
    main()
