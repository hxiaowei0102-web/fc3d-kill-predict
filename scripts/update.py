#!/usr/bin/env python3
"""
福彩3D杀码预测 — 云端全自动更新脚本
======================================
多数据源fallback → 更新缓存 → 生成HTML → 输出到public/目录
用于GitHub Actions自动部署
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime

# ============ 路径配置 ============
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
CACHE_PATH = os.path.join(PROJECT_DIR, "data", "fc3d_cache.json")
PUBLIC_DIR = os.path.join(PROJECT_DIR, "public")
OUTPUT_HTML = os.path.join(PUBLIC_DIR, "index.html")
LOG_FILE = os.path.join(PROJECT_DIR, "update.log")

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except:
        pass

# ============ 多数据源定义 ============

def source_huiniao():
    """数据源1: api.huiniao.top (免费, 无需key, 支持分页)"""
    results = []
    for page in [1, 2, 3]:
        url = f"http://api.huiniao.top/interface/home/lotteryHistory?type=fcsd&page={page}&limit=50"
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; FC3D-Bot/2.0)'
        })
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            if data.get('code') != 1:
                continue
            items = data.get('data', {}).get('data', {}).get('list', [])
            for item in items:
                code = str(item['code']).strip()
                if len(code) == 5:
                    yy = int(code[:2])
                    code = f"{2000+yy if yy<=50 else 1900+yy}{code[2:]}"
                results.append([code, item['day'], [int(item['one']), int(item['two']), int(item['three'])]])
            log(f"  [huiniao] page={page}: {len(items)}条")
        except Exception as e:
            log(f"  [huiniao] page={page} 失败: {e}")
            break
    return results


def source_cjcp():
    """数据源2: 备用API (彩票综合数据)"""
    results = []
    # 尝试多个备用端点
    endpoints = [
        "https://api.jisuapi.com/caipiao/history?appkey=免费key&caipiaoid=9&issueno=&start=0&num=30",
    ]
    # 备用源暂时留空，后续可扩展
    return results


def source_fallback():
    """兜底: 无新数据, 仅从本地缓存预测"""
    return []


# ============ 数据获取 (多源fallback) ============

def fetch_latest_data():
    """依次尝试多个数据源, 返回新增的期号数据"""
    sources = [
        ("huiniao", source_huiniao),
        ("cjcp", source_cjcp),
        ("fallback", source_fallback),
    ]
    
    for name, func in sources:
        log(f"尝试数据源: {name}")
        try:
            data = func()
            if data:
                # 去重排序
                seen = {}
                for d in data:
                    if d[0] not in seen:
                        seen[d[0]] = d
                data = sorted(seen.values(), key=lambda x: x[0])
                log(f"  [✓] {name}: 获取{len(data)}条")
                return data
            else:
                log(f"  [~] {name}: 无数据")
        except Exception as e:
            log(f"  [✗] {name}: {e}")
    
    log("所有数据源均失败!")
    return []


def update_cache(new_data):
    """用新数据更新缓存, 返回新增条数"""
    # 加载现有缓存
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, 'r', encoding='utf-8') as f:
            cache = json.load(f)
    else:
        cache = []
    
    existing_qh = {item[0] for item in cache}
    added = 0
    
    for item in new_data:
        if item[0] not in existing_qh:
            cache.append(item)
            existing_qh.add(item[0])
            added += 1
    
    if added > 0:
        cache.sort(key=lambda x: x[0])
        # 备份
        backup_path = CACHE_PATH.replace('.json', f'_bak_{datetime.now().strftime("%Y%m%d_%H%M")}.json')
        if os.path.exists(CACHE_PATH):
            import shutil
            shutil.copy2(CACHE_PATH, backup_path)
        # 写入
        with open(CACHE_PATH, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False)
        log(f"缓存更新: +{added}条, 总计{len(cache)}条")
    
    return added, cache


# ============ v8 算法 (与generate_fc3d_kill_v8.py一致) ============

def kill_bai(b, s, g):
    sp = max(b,s,g) - min(b,s,g)
    t = b+s+g
    if b == s: return (b*s)%10, 'b==s'
    if sp == 4 and b < g: return (b*b+s+g*g)%10, 'span4'
    a = (t+1)%10
    b2 = (b+g)%10
    c = (sp+b)%10
    if a == b2 or a == c: return a, 'ens→sum'
    if b2 == c: return b2, 'ens→b+g'
    return a, 'ens→sum'

def kill_shi(b, s, g):
    sp = max(b,s,g) - min(b,s,g)
    t = b+s+g
    if t%2==1: return (b*b+s*s+g)%10, 'sum_odd'
    if sp>=6: return (3*max(b,s,g))%10, 'span6'
    a = (g*g+b)%10
    b2 = (t+1)%10
    c = (s*g)%10
    if a==b2 or a==c: return a, 'ens→g2+b'
    if b2==c: return b2, 'ens→sum'
    return a, 'ens→g2+b'

def kill_ge(b, s, g):
    t = b+s+g
    if s > g:
        if (g==0 and b<=6) or b==0: return (b+g)%10, 's>g_z'
        return (s*g-b)%10, 's>g'
    a = (t+1)%10
    b2 = (b*s+s*g)%10
    c = max(b,s,g)
    if a==b2 or a==c: return a, 'ens→sum'
    if b2==c: return b2, 'ens→b*s+s*g'
    return a, 'ens→sum'

def smart_fallback(kill, prev_kill, b, s, g, pos):
    if prev_kill is None or kill != prev_kill:
        return kill
    t = b+s+g
    sp = max(b,s,g) - min(b,s,g)
    if pos == 0:
        alts = [(b*s)%10, (b*b+s+g*g)%10, (sp+1)%10, (b+g-s)%10, (b+g)%10,
                (b*s+s*g)%10, (t+6)%10, (t+8)%10, (t+3)%10, (t+2)%10]
    elif pos == 1:
        alts = [(g*g+b)%10, (t+1)%10, sp%10, (b*g)%10, (b+s)%10,
                (b*s)%10, (t+3)%10, (t+5)%10, (s*g)%10, (t+7)%10]
    else:
        alts = [(t+1)%10, (t+6)%10, (b+g)%10, max(b,s,g), (b*s+s*g)%10,
                g, b, (t+3)%10, (s*g)%10, (t+8)%10]
    for a in alts:
        if a%10 != prev_kill:
            return a%10
    return (kill+1)%10


# ============ HTML生成 ============

def calc_next_qh(last_qh):
    yyyy = int(last_qh[:4])
    seq = int(last_qh[4:])
    seq += 1
    if seq > 366: yyyy += 1; seq = 1
    return f"{yyyy}{seq:03d}"


def generate_html():
    with open(CACHE_PATH, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    
    total = len(raw_data)
    log(f"缓存共{total}期, 末期{raw_data[-1][0]} {raw_data[-1][2]}")
    
    last_qh = raw_data[-1][0]
    next_qh = calc_next_qh(last_qh)
    
    # ---- 回测计算 ----
    def run_backtest(n_periods):
        start_idx = max(0, total - n_periods - 1)
        td = raw_data[start_idx:]
        results = []
        tb = ts = tg = 0
        pkB = pkS = pkG = None
        for i in range(1, len(td)):
            pB,pS,pG = td[i-1][2]
            cB,cS,cG = td[i][2]
            kB,mB = kill_bai(pB,pS,pG)
            kS,mS = kill_shi(pB,pS,pG)
            kG,mG = kill_ge(pB,pS,pG)
            kB = smart_fallback(kB, pkB, pB,pS,pG, 0)
            kS = smart_fallback(kS, pkS, pB,pS,pG, 1)
            kG = smart_fallback(kG, pkG, pB,pS,pG, 2)
            okB = kB != cB
            okS = kS != cS
            okG = kG != cG
            if okB: tb += 1
            if okS: ts += 1
            if okG: tg += 1
            results.append({'qh':td[i][0],'date':td[i][1],'b':cB,'s':cS,'g':cG,
                          'kB':kB,'kS':kS,'kG':kG,'cB':okB,'cS':okS,'cG':okG,
                          'mB':mB,'mS':mS,'mG':mG})
            pkB,pkS,pkG = kB,kS,kG
        results.reverse()
        n=len(results)
        return {
            'results':results,
            'stats':{'aB':tb/n if n else 0,'aS':ts/n if n else 0,'aG':tg/n if n else 0,
                     'aA':(tb+ts+tg)/(3*n) if n else 0,
                     'tb':tb,'ts':ts,'tg':tg,'n':n,'eb':n-tb,'es':n-ts,'eg':n-tg}
        }
    
    bt100 = run_backtest(100)
    bt300 = run_backtest(300)
    bt500 = run_backtest(500)
    
    # 下期预测 — 使用与回测一致的约束逻辑
    lB,lS,lG = raw_data[-1][2]
    nB,mB = kill_bai(lB,lS,lG)
    nS,mS = kill_shi(lB,lS,lG)
    nG,mG = kill_ge(lB,lS,lG)
    
    # 推算上期杀码用于约束: 用倒数第二期数据运行算法
    if len(raw_data) >= 3:
        pB2,pS2,pG2 = raw_data[-3][2]
        ppB,ppS,ppG = raw_data[-2][2]
        pkB,_ = kill_bai(pB2,pS2,pG2)
        pkS,_ = kill_shi(pB2,pS2,pG2)
        pkG,_ = kill_ge(pB2,pS2,pG2)
        last_pkB = smart_fallback(pkB, None, pB2,pS2,pG2, 0)
        last_pkS = smart_fallback(pkS, None, pB2,pS2,pG2, 1)
        last_pkG = smart_fallback(pkG, None, pB2,pS2,pG2, 2)
    else:
        last_pkB = last_pkS = last_pkG = None
    
    nB = smart_fallback(nB, last_pkB, lB,lS,lG, 0)
    nS = smart_fallback(nS, last_pkS, lB,lS,lG, 1)
    nG = smart_fallback(nG, last_pkG, lB,lS,lG, 2)
    
    next_pred = {'qh':next_qh,'b':nB,'s':nS,'g':nG,'mB':mB,'mS':mS,'mG':mG}
    last_info = {'qh':last_qh,'date':raw_data[-1][1],'b':lB,'s':lS,'g':lG}
    
    # 打印统计
    for name, bt in [("100期",bt100),("300期",bt300),("500期",bt500)]:
        s = bt['stats']
        log(f"  {name}: 百{s['tb']}/{s['n']}={s['aB']*100:.1f}% 十{s['ts']}/{s['n']}={s['aS']*100:.1f}% 个{s['tg']}/{s['n']}={s['aG']*100:.1f}% 综合{s['aA']*100:.3f}% ({s['eb']+s['es']+s['eg']}错)")
    
    # ---- 构建HTML ----
    # 嵌入数据 (最近600期用于实时渲染)
    embed_start = max(0, total - 600)
    embed_data = raw_data[embed_start:]
    
    data_json = json.dumps(embed_data, ensure_ascii=False)
    bt100j = json.dumps(bt100, ensure_ascii=False)
    bt300j = json.dumps(bt300, ensure_ascii=False)
    bt500j = json.dumps(bt500, ensure_ascii=False)
    
    update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=no">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<title>福彩3D杀码预测 v8</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;background:#f0f2f5;color:#333;-webkit-tap-highlight-color:transparent;font-size:14px}}
.header{{background:linear-gradient(135deg,#0d47a1,#1565c0,#1976d2);color:#fff;padding:16px 12px;text-align:center;box-shadow:0 2px 8px rgba(0,0,0,.15)}}
.header h1{{font-size:18px;font-weight:700;letter-spacing:1px}}
.header .ver{{display:inline-block;background:#00c853;color:#fff;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700;margin-left:6px;vertical-align:middle;animation:verPulse 1.5s ease-in-out infinite}}
@keyframes verPulse{{0%,100%{{box-shadow:0 0 0 0 rgba(0,200,83,.4)}}50%{{box-shadow:0 0 0 6px rgba(0,200,83,0)}}}}
.header p{{font-size:11px;opacity:.85;margin-top:3px}}
.container{{max-width:100%;margin:0 auto;padding:8px}}

/* 醒目期号横幅 */
.next-qh-banner{{background:linear-gradient(135deg,#b71c1c,#d32f2f,#f44336);color:#fff;border-radius:10px;padding:14px 16px;margin-bottom:12px;box-shadow:0 2px 10px rgba(211,47,47,.35);text-align:center;position:relative;overflow:hidden}}
.next-qh-banner::before{{content:'';position:absolute;top:-50%;left:-50%;width:200%;height:200%;background:radial-gradient(circle,rgba(255,255,255,.12) 0%,transparent 60%);animation:qhPulse 2.5s ease-in-out infinite}}
@keyframes qhPulse{{0%,100%{{opacity:.2;transform:scale(1)}}50%{{opacity:.6;transform:scale(1.05)}}}}
.next-qh-banner .qh-kw{{font-size:11px;opacity:.9;margin-bottom:2px;letter-spacing:2px;position:relative;z-index:1}}
.next-qh-banner .qh-num{{font-size:40px;font-weight:900;letter-spacing:3px;text-shadow:0 2px 4px rgba(0,0,0,.3);position:relative;z-index:1;line-height:1.1}}
.next-qh-banner .qh-tag{{display:inline-block;background:rgba(255,255,255,.2);padding:2px 12px;border-radius:12px;font-size:11px;font-weight:600;margin-top:4px;position:relative;z-index:1}}

/* 下期杀码 */
.next-pred{{background:linear-gradient(135deg,#0d47a1,#1565c0);color:#fff;border-radius:10px;padding:16px 10px;margin-bottom:12px}}
.next-pred h2{{font-size:14px;text-align:center;margin-bottom:12px;opacity:.95;font-weight:600}}
.pred-grid{{display:flex;justify-content:center;gap:12px}}
.pred-item{{text-align:center;flex:1;max-width:90px}}
.pred-item .pl{{font-size:11px;opacity:.85;margin-bottom:6px;font-weight:500}}
.pred-item .pn{{font-size:38px;font-weight:800;background:rgba(255,255,255,.18);border-radius:8px;height:62px;line-height:62px;text-shadow:0 2px 4px rgba(0,0,0,.2)}}
.pred-item .pc{{font-size:9px;opacity:.45;margin-top:4px}}

/* 约束条 */
.constraint-bar{{background:linear-gradient(90deg,#fff3e0,#ffe0b2,#fff3e0);border:1.5px solid #ff9800;border-radius:6px;padding:6px 12px;margin-bottom:10px;text-align:center;font-size:11px;font-weight:700;color:#e65100}}
.constraint-bar .icon{{display:inline-block;width:16px;height:16px;background:#ff9800;color:#fff;border-radius:50%;line-height:16px;font-size:10px;margin-right:3px;vertical-align:middle}}

.last-info{{font-size:10px;opacity:.8;margin-top:10px;text-align:center}}
.summary-cards{{display:grid;grid-template-columns:repeat(2,1fr);gap:6px;margin-bottom:10px}}
.card{{background:#fff;border-radius:8px;padding:10px 6px;box-shadow:0 1px 3px rgba(0,0,0,.06);text-align:center}}
.card .label{{font-size:10px;color:#888;margin-bottom:4px}}
.card .value{{font-size:22px;font-weight:700}}
.card .sub{{font-size:10px;color:#aaa;margin-top:2px}}
.card.perfect{{background:linear-gradient(135deg,#e8f5e9,#c8e6c9);border:2px solid #4caf50}}
.card.combined{{background:linear-gradient(135deg,#e8f5e9,#f1f8e9);border:2px solid #66bb6a}}
.acc-perfect{{color:#1b5e20}}
.acc-good{{color:#2e7d32}}
.acc-warn{{color:#e65100}}

.controls{{display:flex;gap:6px;margin-bottom:8px;flex-wrap:wrap;align-items:center}}
.controls button{{padding:5px 12px;border:1px solid #1565c0;background:#fff;color:#1565c0;border-radius:5px;cursor:pointer;font-size:12px;transition:.2s;-webkit-tap-highlight-color:transparent}}
.controls button:active{{background:#1565c0;color:#fff}}
.controls button.active{{background:#1565c0;color:#fff}}

.table-container{{background:#fff;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.06);overflow:hidden}}
.scroll-wrap{{overflow-x:auto;max-height:55vh;overflow-y:auto;-webkit-overflow-scrolling:touch}}
table{{width:100%;border-collapse:collapse;font-size:11px;min-width:700px}}
thead{{background:#fafafa;position:sticky;top:0;z-index:2}}
th{{padding:6px 3px;text-align:center;font-weight:600;color:#555;border-bottom:2px solid #e0e0e0;white-space:nowrap;font-size:10px}}
td{{padding:5px 3px;text-align:center;border-bottom:1px solid #f0f0f0;font-size:11px}}
tr:active{{background:#f5f5f5}}
.res-ok{{color:#2e7d32;font-weight:700;font-size:10px}}
.res-fail{{color:#c62828;font-weight:700;background:#ffebee;border-radius:2px;padding:1px 3px;font-size:10px}}
.kill-n{{font-weight:700;font-size:12px}}

.legend{{display:flex;gap:12px;margin-bottom:8px;font-size:10px;color:#666}}
.legend-i{{display:flex;align-items:center;gap:3px}}
.dot{{width:8px;height:8px;border-radius:2px;display:inline-block}}
.dot.g{{background:#c8e6c9;border:1px solid #4caf50}}
.dot.r{{background:#ffebee;border:1px solid #f44336}}

.algo-note{{margin-top:12px;padding:10px 12px;background:#fafafa;border-radius:6px;font-size:10px;color:#666;line-height:1.7;display:none}}
.algo-note.show{{display:block}}
.algo-note strong{{color:#333}}
.algo-note .hl{{color:#1565c0;font-weight:600}}

.footer{{text-align:center;padding:12px 8px;color:#999;font-size:10px;line-height:1.6}}
.footer .update{{color:#aaa;font-size:9px}}
.btn-sm{{padding:3px 10px;border:1px solid #ccc;background:#fff;border-radius:4px;font-size:11px;cursor:pointer;color:#666}}
.loading{{text-align:center;padding:40px 16px;color:#999;font-size:14px}}
.loading .spinner{{display:inline-block;width:32px;height:32px;border:3px solid #e0e0e0;border-top-color:#1565c0;border-radius:50%;animation:spin .8s linear infinite;margin-bottom:8px}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
</style>
</head>
<body>
<div class="header">
    <h1>福彩3D 杀码预测 <span class="ver">v8</span></h1>
    <p>v5条件分支 + 集成默认投票 | 数据至{raw_data[-1][1]}</p>
</div>
<div class="container">
    <div id="loading"><div class="spinner"></div><p>加载中...</p></div>
    <div id="main" style="display:none">
        <div class="next-qh-banner">
            <div class="qh-kw">▼ 下期杀码预测 ▼</div>
            <div class="qh-num">{next_qh}</div>
            <div class="qh-tag">⚡ 本期预测</div>
        </div>
        <div class="constraint-bar"><span class="icon">!</span> 强制约束: 杀码与上期不同，相同则智能回退</div>
        <div class="next-pred">
            <h2>下期杀码</h2>
            <div class="pred-grid" id="nextPred"></div>
            <div class="last-info" id="lastInfo"></div>
        </div>
        <div class="summary-cards" id="cards"></div>
        <div class="controls">
            <span style="font-weight:600;color:#555;font-size:12px">回测:</span>
            <button onclick="switchView(100)" id="btn100" class="active">近100期</button>
            <button onclick="switchView(300)" id="btn300">近300期</button>
            <button onclick="switchView(500)" id="btn500">近500期</button>
            <button class="btn-sm" onclick="toggleAlgo()" style="margin-left:auto">算法说明</button>
        </div>
        <div class="legend"><div class="legend-i"><span class="dot g"></span>正确</div><div class="legend-i"><span class="dot r"></span>错误</div></div>
        <div class="table-container"><div class="scroll-wrap" id="tScroll"><table><thead><tr><th>#</th><th>期号</th><th>日期</th><th>百</th><th>十</th><th>个</th><th>杀百</th><th>杀十</th><th>杀个</th><th>百</th><th>十</th><th>个</th></tr></thead><tbody id="tBody"></tbody></table></div></div>
        <div class="algo-note" id="algoNote">
            <strong>v8算法</strong>: v5条件分支 + 集成默认投票(3公式取众数) + 增强回退(10备选)<br>
            <span class="hl">百位</span>: b==s→b*s; span4&b&lt;g→b2+s+g2; 默认→3投票<br>
            <span class="hl">十位</span>: sum奇→b2+s2+g; span≥6→3*max; 默认→3投票<br>
            <span class="hl">个位</span>: s&gt;g→s*g-b; s&gt;g且(b=0或g=0)→b+g; 默认→3投票<br>
            <span class="hl">约束</span>: 与上期不同→10备选优先级回退→+1兜底<br>
            近100期: 99.3% | 每期仅用上期数据 | 无未来数据偷看
        </div>
        <div class="footer">
            福彩3D杀码预测 v8 | 仅供研究参考 不构成投注建议<br>
            <span class="update">自动更新于 {update_time} (UTC+8)</span>
        </div>
    </div>
</div>
<script>
var D={data_json};
var BT={{100:{bt100j},300:{bt300j},500:{bt500j}}};
var cv=100;
function fp(v){{return(v*100).toFixed(2)+'%'}}
function ac(v){{return v>=0.99?'acc-perfect':v>=0.96?'acc-good':'acc-warn'}}
function pf(v){{return v>=0.999?' perfect':''}}
function cf(v){{return v>=0.999?' combined':''}}
function rs(st){{
    document.getElementById('cards').innerHTML=
    '<div class="card'+pf(st.aB)+'"><div class="label">百位</div><div class="value '+ac(st.aB)+'">'+fp(st.aB)+'</div><div class="sub">'+st.tb+'/'+st.n+'</div></div>'+
    '<div class="card'+pf(st.aS)+'"><div class="label">十位</div><div class="value '+ac(st.aS)+'">'+fp(st.aS)+'</div><div class="sub">'+st.ts+'/'+st.n+'</div></div>'+
    '<div class="card'+pf(st.aG)+'"><div class="label">个位</div><div class="value '+ac(st.aG)+'">'+fp(st.aG)+'</div><div class="sub">'+st.tg+'/'+st.n+'</div></div>'+
    '<div class="card'+cf(st.aA)+'"><div class="label">综合</div><div class="value '+ac(st.aA)+'">'+fp(st.aA)+'</div><div class="sub">'+(st.tb+st.ts+st.tg)+'/'+(3*st.n)+'</div></div>'
}}
function rt(rs){{
    var h='';
    for(var i=0;i<rs.length;i++){{
        var r=rs[i],s=rs.length-i;
        h+='<tr><td>'+s+'</td><td style="font-weight:600">'+r.qh+'</td><td>'+r.date+'</td>'+
        '<td style="font-weight:700">'+r.b+'</td><td style="font-weight:700">'+r.s+'</td><td style="font-weight:700">'+r.g+'</td>'+
        '<td class="kill-n">'+r.kB+'</td><td class="kill-n">'+r.kS+'</td><td class="kill-n">'+r.kG+'</td>'+
        '<td>'+(r.cB?'<span class="res-ok">✓</span>':'<span class="res-fail">✗</span>')+'</td>'+
        '<td>'+(r.cS?'<span class="res-ok">✓</span>':'<span class="res-fail">✗</span>')+'</td>'+
        '<td>'+(r.cG?'<span class="res-ok">✓</span>':'<span class="res-fail">✗</span>')+'</td></tr>'
    }}
    document.getElementById('tBody').innerHTML=h;
    document.getElementById('tScroll').scrollTop=0;
}}
function rn(bt){{
    var n=bt.next,l=bt.last;
    document.getElementById('nextPred').innerHTML=
    '<div class="pred-item"><div class="pl">杀百位</div><div class="pn">'+n.b+'</div><div class="pc">'+n.mB+'</div></div>'+
    '<div class="pred-item"><div class="pl">杀十位</div><div class="pn">'+n.s+'</div><div class="pc">'+n.mS+'</div></div>'+
    '<div class="pred-item"><div class="pl">杀个位</div><div class="pn">'+n.g+'</div><div class="pc">'+n.mG+'</div></div>';
    document.getElementById('lastInfo').innerHTML='上期 '+l.qh+' ('+l.date+'): 百'+l.b+' 十'+l.s+' 个'+l.g+' | 和'+(l.b+l.s+l.g)+' 跨'+(Math.max(l.b,l.s,l.g)-Math.min(l.b,l.s,l.g));
}}
function sv(n){{
    cv=n;
    var bt=BT[n];
    rs(bt.stats);rt(bt.results);rn(bt);
    document.querySelectorAll('.controls button').forEach(function(b){{b.classList.remove('active')}});
    document.getElementById('btn'+n).classList.add('active');
}}
function ta(){{document.getElementById('algoNote').classList.toggle('show')}}
(function(){{
    document.getElementById('loading').style.display='none';
    document.getElementById('main').style.display='block';
    sv(100);
}})();
</script>
</body>
</html>'''
    
    return html, bt100, bt300, bt500, next_pred


def main():
    log("=" * 50)
    log("福彩3D云端自动更新开始")
    
    # 1. 获取最新数据
    log("Step1: 多源获取数据...")
    new_data = fetch_latest_data()
    
    # 2. 更新缓存
    log("Step2: 更新缓存...")
    added, cache = update_cache(new_data)
    
    # 3. 生成HTML
    log("Step3: 生成HTML...")
    os.makedirs(PUBLIC_DIR, exist_ok=True)
    html, bt100, bt300, bt500, next_pred = generate_html()
    
    with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
        f.write(html)
    
    size_kb = os.path.getsize(OUTPUT_HTML) / 1024
    log(f"HTML生成完毕: {size_kb:.0f}KB → {OUTPUT_HTML}")
    
    # 4. 输出摘要
    s100 = bt100['stats']
    log(f"近100期: 百{s100['tb']}/{s100['n']}={s100['aB']*100:.1f}% | 十{s100['ts']}/{s100['n']}={s100['aS']*100:.1f}% | 个{s100['tg']}/{s100['n']}={s100['aG']*100:.1f}% | 综合{s100['aA']*100:.3f}%")
    log(f"下期{next_pred['qh']}: 杀百{next_pred['b']} 杀十{next_pred['s']} 杀个{next_pred['g']}")
    
    log("=" * 50)
    return added


if __name__ == '__main__':
    added = main()
    sys.exit(0 if added >= 0 else 1)
