#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 / 更新 index.html 里的 DOC 27「附录：GitHub Agent 全景图与选型指南」。

数据源：docs/data/agent-landscape-<snapshot>.json（由上游 agent-landscape 的
data.json + annotations.json + tracks.json 合并而来，见 docs/27 第 9 节）。

用法：
    python scripts/build_landscape.py            # 只渲染并打印统计，不写文件
    python scripts/build_landscape.py --apply    # 写入 index.html（按标记替换，可重复执行）
    python scripts/build_landscape.py --check    # 只校验 index.html 与数据的一致性

页面里用四个标记块承载本章，--apply 只替换标记之间的内容：
    /* LANDSCAPE:CSS:BEGIN */  ...  /* LANDSCAPE:CSS:END */
    <!-- LANDSCAPE:NAV:BEGIN --> ... <!-- LANDSCAPE:NAV:END -->
    <!-- LANDSCAPE:SECTION:BEGIN --> ... <!-- LANDSCAPE:SECTION:END -->
    <!-- LANDSCAPE:JS:BEGIN --> ... <!-- LANDSCAPE:JS:END -->
"""

import argparse
import glob
import html
import json
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, 'index.html')
STANDALONE = os.path.join(ROOT, 'landscape.html')

STATUS_LABEL = {
    'active': '活跃',
    'maintained': '维护中',
    'stale': '沉寂',
    'archived': '已归档',
}
STATUS_CLASS = {
    'active': 'ls-st-active',
    'maintained': 'ls-st-maintained',
    'stale': 'ls-st-stale',
    'archived': 'ls-st-archived',
}
DIFF_CLASS = {'易': 'ls-d-easy', '中': 'ls-d-medium', '难': 'ls-d-hard'}


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def esc(text):
    return html.escape(str(text), quote=False)


def esc_attr(text):
    return html.escape(str(text), quote=True)


def wan(n):
    """Chinese big-number style: 15.0 万 / 9,279."""
    if n >= 10000:
        return ('%.1f' % (n / 10000.0)).replace('.0', '') + ' 万'
    return '{:,}'.format(n)


def intcomma(n):
    return '{:,}'.format(n)


def load_data(path=None):
    if path is None:
        candidates = sorted(glob.glob(os.path.join(ROOT, 'docs', 'data', 'agent-landscape-*.json')))
        if not candidates:
            sys.exit('找不到数据文件 docs/data/agent-landscape-*.json')
        path = candidates[-1]
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    if not data.get('projects') or not data.get('tracks'):
        sys.exit('数据文件缺少 projects / tracks')
    return data


def compute_stats(data):
    projects = data['projects']
    tracks = data['tracks']
    total = sum(p['stars'] for p in projects)
    by_cat = {}
    for p in projects:
        by_cat.setdefault(p['cat'], []).append(p)
    stars_sorted = sorted(projects, key=lambda p: -p['stars'])
    top20 = sum(p['stars'] for p in stars_sorted[:20])
    top10 = sum(p['stars'] for p in stars_sorted[:10])
    stars_values = sorted(p['stars'] for p in projects)
    median = stars_values[len(stars_values) // 2]
    status = Counter(p['status'] for p in projects)
    diff = Counter(p['diff'] for p in projects)
    langs = Counter(p['lang'] for p in projects)
    lic = Counter(p['lic'] for p in projects)
    standard_lic = lic.get('MIT', 0) + lic.get('Apache-2.0', 0)
    created = Counter(p['created_at'][:4] for p in projects)
    return {
        'n': len(projects),
        'n_tracks': len(tracks),
        'total': total,
        'by_cat': by_cat,
        'max_track_stars': max((sum(p['stars'] for p in v) for v in by_cat.values()), default=1),
        'top20_share': 100.0 * top20 / total if total else 0,
        'top10_share': 100.0 * top10 / total if total else 0,
        'median': median,
        'status': status,
        'diff': diff,
        'langs': langs,
        'lic': lic,
        'standard_lic': standard_lic,
        'nonstd_lic': len(projects) - standard_lic,
        'created': created,
        'new_2y': sum(created.get(y, 0) for y in ('2025', '2026')),
    }


# --------------------------------------------------------------------------- #
# CSS
# --------------------------------------------------------------------------- #
CSS = r"""/* LANDSCAPE:CSS:BEGIN */
.ls{margin:18px 0 8px}
.ls-bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;padding:12px;border:1px solid var(--line);border-radius:14px;background:var(--panel2)}
.ls-bar input[type=search]{flex:1 1 260px;min-width:200px;padding:8px 12px;border:1px solid var(--line);border-radius:9px;background:var(--panel);color:var(--ink);font:inherit;font-size:14px}
.ls-bar input[type=search]:focus{outline:2px solid color-mix(in srgb,var(--accent) 45%,transparent);outline-offset:1px}
.ls-bar select{padding:8px 10px;border:1px solid var(--line);border-radius:9px;background:var(--panel);color:var(--ink);font:inherit;font-size:13.5px}
.ls-btn{padding:8px 12px;border:1px solid var(--line);border-radius:9px;background:var(--panel);color:var(--ink);font:inherit;font-size:13.5px;cursor:pointer}
.ls-btn:hover{border-color:var(--accent)}
.ls-btn[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);color:#fff}
.ls-chips{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0 6px}
.ls-chip{padding:5px 10px;border:1px solid var(--line);border-radius:999px;background:var(--panel);color:var(--muted);font:inherit;font-size:12.5px;cursor:pointer;display:inline-flex;gap:6px;align-items:center}
.ls-chip i{font-style:normal;font-size:11px;opacity:.72}
.ls-chip:hover{border-color:var(--accent);color:var(--ink)}
.ls-chip.on{background:var(--accent);border-color:var(--accent);color:#fff}
.ls-chip.on i{opacity:.85}
.ls-count{font-size:13px;color:var(--muted);margin:8px 0 16px}
.ls-count b{color:var(--ink)}
.ls-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:14px 0 18px}
.ls-stat{border:1px solid var(--line);border-radius:12px;padding:12px 14px;background:var(--panel2)}
.ls-stat b{display:block;font-size:24px;line-height:1.25;font-variant-numeric:tabular-nums}
.ls-stat span{font-size:12px;color:var(--muted)}
.ls-bars{border:1px solid var(--line);border-radius:12px;background:var(--panel2);padding:12px 14px;margin:14px 0}
.ls-bar-row{display:grid;grid-template-columns:190px 1fr 86px;gap:10px;align-items:center;margin:5px 0;font-size:12.5px}
.ls-bar-name{color:var(--ink);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ls-bar-name span{color:var(--muted);margin-left:4px}
.ls-bar-track{height:9px;background:color-mix(in srgb,var(--muted) 16%,transparent);border-radius:999px;overflow:hidden}
.ls-bar-fill{display:block;height:100%;border-radius:999px;background:linear-gradient(90deg,var(--accent),var(--accent2))}
.ls-bar-val{text-align:right;color:var(--muted);font-variant-numeric:tabular-nums}
.ls-group{margin:20px 0 6px}
.ls-gh{display:flex;flex-wrap:wrap;gap:6px 12px;align-items:baseline;border-bottom:1px solid var(--line);padding-bottom:8px;margin:0 0 12px}
.ls-gh h3{font-size:17px;margin:0;border:0;padding:0}
.ls-gh .ls-gi{font-size:11px;color:var(--accent);letter-spacing:.1em;margin-right:7px}
.ls-gsub{font-size:12.5px;color:var(--muted)}
.ls-gmeta{margin-left:auto;font-size:12.5px;color:var(--muted)}
.ls-gmeta b{color:var(--ink);font-variant-numeric:tabular-nums}
.ls-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}
.ls-card{border:1px solid var(--line);border-radius:12px;background:var(--panel);padding:12px 13px;display:flex;flex-direction:column;gap:6px}
.ls-card:hover{border-color:color-mix(in srgb,var(--accent) 45%,var(--line))}
.ls-ctop{display:flex;gap:8px;align-items:baseline;justify-content:space-between}
.ls-repo{font-weight:700;font-size:14px;word-break:break-all}
.ls-stars{font-size:12px;color:#a5760a;white-space:nowrap;font-variant-numeric:tabular-nums}
html[data-theme="dark"] .ls-stars{color:#e3b341}
.ls-pitch{margin:0;font-size:13.5px;font-weight:600;line-height:1.5}
.ls-aud{margin:0;font-size:12.5px;color:var(--muted)}
.ls-note{margin:0;font-size:12.5px;color:var(--muted);line-height:1.55}
.ls-meta{display:flex;flex-wrap:wrap;gap:5px;margin-top:auto;padding-top:6px}
.ls-tag{font-size:11px;padding:2px 7px;border-radius:6px;background:var(--panel2);color:var(--muted);border:1px solid var(--line);white-space:nowrap}
.ls-tag.ls-d-easy{color:#0b7a4b;border-color:#b9e2cb;background:#eefaf3}
.ls-tag.ls-d-medium{color:#8a5a00;border-color:#e8d5a8;background:#fdf6e6}
.ls-tag.ls-d-hard{color:#9c2f2f;border-color:#e8bcbc;background:#fdf0f0}
.ls-tag.ls-st-active{color:#0b7a4b}
.ls-tag.ls-st-maintained{color:#8a5a00}
.ls-tag.ls-st-stale,.ls-tag.ls-st-archived{color:#9c2f2f}
html[data-theme="dark"] .ls-tag.ls-d-easy,html[data-theme="dark"] .ls-tag.ls-st-active{color:#5fd39b;border-color:#255b41;background:#12281f}
html[data-theme="dark"] .ls-tag.ls-d-medium,html[data-theme="dark"] .ls-tag.ls-st-maintained{color:#e0b457;border-color:#5a4620;background:#241f12}
html[data-theme="dark"] .ls-tag.ls-d-hard,html[data-theme="dark"] .ls-tag.ls-st-stale,html[data-theme="dark"] .ls-tag.ls-st-archived{color:#ef8b8b;border-color:#5c2a2a;background:#261414}
.ls-empty{margin:18px 0;padding:18px;border:1px dashed var(--line);border-radius:12px;color:var(--muted);text-align:center}
.ls-hidden{display:none!important}
@media (max-width:1000px){.ls-bar-row{grid-template-columns:130px 1fr 76px}.ls-grid{grid-template-columns:1fr}}
@media print{.ls-bar,.ls-chips,.ls-count{display:none!important}.ls-card{break-inside:avoid}.ls-grid{grid-template-columns:1fr 1fr}}
/* LANDSCAPE:CSS:END */"""


# --------------------------------------------------------------------------- #
# JS
# --------------------------------------------------------------------------- #
JS = r"""<!-- LANDSCAPE:JS:BEGIN -->
<script>
(function(){
  var root=document.getElementById('agent-landscape');
  if(!root) return;
  var q=document.getElementById('ls-q'), langSel=document.getElementById('ls-lang'),
      diffSel=document.getElementById('ls-diff'), sortSel=document.getElementById('ls-sort'),
      actBtn=document.getElementById('ls-act'), resetBtn=document.getElementById('ls-reset'),
      countEl=document.getElementById('ls-count'), emptyEl=document.getElementById('ls-empty'),
      cards=[].slice.call(document.querySelectorAll('.ls-card')),
      groups=[].slice.call(document.querySelectorAll('.ls-group')),
      chips=[].slice.call(document.querySelectorAll('.ls-chip')),
      curCat='all';
  // 只有独立浏览页（landscape.html）把筛选状态写进地址栏：
  // 手册页的 #xxx 是章节锚点，不能被覆盖。
  var hashMode=root.getAttribute('data-hash')==='1';
  var loc=(typeof window!=='undefined'&&window.location)?window.location:null;
  var hist=(typeof window!=='undefined'&&window.history)?window.history:null;

  function fmt(n){ return n>=10000 ? (n/10000).toFixed(1).replace(/\.0$/,'')+' 万' : n.toLocaleString('en-US'); }
  function on(){ return actBtn.getAttribute('aria-pressed')==='true'; }

  function apply(){
    var raw=q.value.trim().toLowerCase();
    var kws=raw.split(/\s+/).filter(Boolean);
    var lg=langSel.value||'', df=diffSel.value||'', actOnly=on(), shown=0;

    cards.forEach(function(c){
      var ok=(curCat==='all'||c.dataset.cat===curCat)
        && (!lg||c.dataset.lang===lg)
        && (!df||c.dataset.diff===df)
        && (!actOnly||c.dataset.act==='1');
      if(ok&&kws.length){
        var hay=c.dataset.search||'';
        ok=kws.every(function(k){ return hay.indexOf(k)>-1; });
      }
      c.classList.toggle('ls-hidden',!ok);
      if(ok) shown++;
    });

    groups.forEach(function(g){
      var grid=g.querySelector('.ls-grid');
      var list=[].slice.call(grid.children);
      list.sort(function(a,b){
        return (sortSel.value||'stars')==='upd'
          ? (b.dataset.upd||'').localeCompare(a.dataset.upd||'')
          : (+b.dataset.stars)-(+a.dataset.stars);
      });
      list.forEach(function(el){ grid.appendChild(el); });
      var vis=list.filter(function(el){ return !el.classList.contains('ls-hidden'); });
      g.classList.toggle('ls-hidden',!vis.length);
      g.querySelector('.ls-gn').textContent=vis.length;
      var sum=vis.reduce(function(n,el){ return n+(+el.dataset.stars); },0);
      g.querySelector('.ls-gs').textContent=fmt(sum);
    });

    emptyEl.classList.toggle('ls-hidden',shown>0);
    countEl.innerHTML='显示 <b>'+shown+'</b> / '+cards.length+' 个项目 · '+groups.length+' 个赛道';
    syncHash();
  }

  var hashTimer=null;
  function syncHash(){
    if(!hashMode||!loc||!hist||!hist.replaceState) return;
    clearTimeout(hashTimer);
    hashTimer=setTimeout(function(){
      var p=new URLSearchParams();
      if(curCat!=='all') p.set('cat',curCat);
      if(q.value.trim()) p.set('q',q.value.trim());
      if(langSel.value) p.set('lang',langSel.value);
      if(diffSel.value) p.set('diff',diffSel.value);
      if(on()) p.set('act','1');
      var sv=sortSel.value||'stars';
      if(sv!=='stars') p.set('sort',sv);
      var h=p.toString();
      try{
        hist.replaceState(null,'', h ? '#'+h : loc.pathname+loc.search);
      }catch(e){}
    },250);
  }

  function readHash(){
    if(!hashMode||!loc||!loc.hash) return;
    var p;
    try{ p=new URLSearchParams(loc.hash.replace(/^#/,'')); }catch(e){ return; }
    if(p.get('q')!==null) q.value=p.get('q');
    var lg=p.get('lang'); if(lg) langSel.value=lg;
    var df=p.get('diff'); if(df) diffSel.value=df;
    var st=p.get('sort'); if(st) sortSel.value=st;
    if(p.get('act')==='1') actBtn.setAttribute('aria-pressed','true');
    var cat=p.get('cat')||'all';
    curCat='all';
    chips.forEach(function(c){
      var hit=c.dataset.cat===cat;
      c.classList.toggle('on',hit);
      c.setAttribute('aria-pressed',String(hit));
      if(hit) curCat=c.dataset.cat;
    });
  }

  function reset(){
    q.value=''; langSel.value=''; diffSel.value=''; sortSel.value='stars';
    actBtn.setAttribute('aria-pressed','false');
    curCat='all';
    chips.forEach(function(c){
      var isAll=c.dataset.cat==='all';
      c.classList.toggle('on',isAll);
      c.setAttribute('aria-pressed',String(isAll));
    });
    apply();
  }

  chips.forEach(function(ch){
    ch.addEventListener('click',function(){
      chips.forEach(function(x){ x.classList.remove('on'); x.setAttribute('aria-pressed','false'); });
      ch.classList.add('on');
      ch.setAttribute('aria-pressed','true');
      curCat=ch.dataset.cat;
      apply();
    });
  });
  actBtn.addEventListener('click',function(){
    actBtn.setAttribute('aria-pressed',on()?'false':'true');
    apply();
  });
  resetBtn.addEventListener('click',reset);
  q.addEventListener('input',apply);
  q.addEventListener('keydown',function(e){
    if(e.key==='Escape'&&q.value){ q.value=''; apply(); }
  });
  langSel.addEventListener('change',apply);
  diffSel.addEventListener('change',apply);
  sortSel.addEventListener('change',apply);

  // 明暗主题（与手册共用 localStorage 键）
  var themeBtn=document.getElementById('ls-theme');
  try{
    var saved=localStorage.getItem('manual-theme');
    if(saved) document.documentElement.setAttribute('data-theme',saved);
  }catch(e){}
  if(themeBtn){
    themeBtn.addEventListener('click',function(){
      var cur=document.documentElement.getAttribute('data-theme')==='dark'?'light':'dark';
      document.documentElement.setAttribute('data-theme',cur);
      themeBtn.textContent=cur==='dark'?'切换白天':'切换夜间';
      try{ localStorage.setItem('manual-theme',cur); }catch(e){}
    });
  }

  // 独立页支持 / 聚焦搜索（手册页有自己的全局快捷键，不抢）
  if(hashMode){
    document.addEventListener('keydown',function(e){
      var tag=(document.activeElement&&document.activeElement.tagName)||'';
      if(e.key==='/' && !/^(INPUT|SELECT|TEXTAREA)$/.test(tag)){ e.preventDefault(); q.focus(); q.select(); }
    });
  }

  readHash();
  apply();
})();
</script>
<!-- LANDSCAPE:JS:END -->"""


# --------------------------------------------------------------------------- #
# section
# --------------------------------------------------------------------------- #
def render_cards(data, stats):
    tracks = data['tracks']
    by_cat = stats['by_cat']
    out = []
    for i, t in enumerate(tracks, 1):
        items = sorted(by_cat.get(t['cat'], []), key=lambda p: (-p['stars'], p['name'].lower()))
        if not items:
            continue
        total = sum(p['stars'] for p in items)
        out.append('<section class="ls-group" data-cat="%s">' % esc_attr(t['cat']))
        out.append('<div class="ls-gh"><h3><span class="ls-gi">%02d</span>%s</h3>'
                   '<span class="ls-gsub">%s</span>'
                   '<span class="ls-gmeta"><b class="ls-gn">%d</b> 个项目 · <b class="ls-gs">%s</b>星标</span></div>'
                   % (i, esc(t['title']), esc(t['sub']), len(items), wan(total)))
        out.append('<div class="ls-grid">')
        for p in items:
            topics = ' '.join(p.get('topics') or [])
            search = ' '.join([
                p['name'], p['pitch'], p['aud'], p['note'], topics,
                p['lang'], p['lic'], t['title'],
            ]).lower()
            title = '★ %s · 创建 %s · 最近提交 %s' % (
                intcomma(p['stars']), p.get('created_at') or '未知', p.get('pushed_at') or '未知')
            if p.get('homepage'):
                title += ' · ' + p['homepage']
            out.append(
                '<article class="ls-card" data-cat="%s" data-lang="%s" data-diff="%s" data-act="%s" '
                'data-stars="%d" data-upd="%s" data-name="%s" data-search="%s">'
                % (esc_attr(p['cat']), esc_attr(p['lang']), esc_attr(p['diff']),
                   '1' if p['status'] == 'active' else '0',
                   p['stars'], esc_attr(p.get('pushed_at') or ''), esc_attr(p['name'].lower()),
                   esc_attr(search)))
            out.append('<div class="ls-ctop"><a class="ls-repo" href="%s" target="_blank" rel="noopener noreferrer">%s</a>'
                       '<span class="ls-stars" title="%s">★ %s</span></div>'
                       % (esc_attr(p['url']), esc(p['name']), esc_attr(title), wan(p['stars'])))
            out.append('<p class="ls-pitch">%s</p>' % esc(p['pitch']))
            out.append('<p class="ls-aud">适合：%s</p>' % esc(p['aud']))
            out.append('<p class="ls-note">%s</p>' % esc(p['note']))
            out.append('<div class="ls-meta"><span class="ls-tag">%s</span>'
                       '<span class="ls-tag %s">门槛 %s</span><span class="ls-tag">%s</span>'
                       '<span class="ls-tag %s">%s</span></div>'
                       % (esc(p['lang']), DIFF_CLASS.get(p['diff'], ''), esc(p['diff']),
                          esc(p['lic'] or '见仓库'), STATUS_CLASS.get(p['status'], ''),
                          STATUS_LABEL.get(p['status'], p['status'])))
            out.append('</article>')
        out.append('</div></section>')
    return '\n'.join(out)


def render_toolbar(stats):
    opts = ''.join('<option value="%s">%s（%d）</option>' % (esc_attr(k), esc(k), v)
                   for k, v in stats['langs'].most_common())
    return ('<div class="ls-bar">\n'
            '<input type="search" id="ls-q" placeholder="搜索：仓库名 / 中文定位 / 适合人群 / 标签（空格分词）" aria-label="搜索项目" autocomplete="off">\n'
            '<select id="ls-lang" aria-label="语言"><option value="">全部语言</option>' + opts + '</select>\n'
            '<select id="ls-diff" aria-label="门槛"><option value="">全部门槛</option><option value="易">易 · 装完能跑</option><option value="中">中 · 要改代码</option><option value="难">难 · 要懂架构</option></select>\n'
            '<select id="ls-sort" aria-label="排序"><option value="stars">按星数排序</option><option value="upd">按最近更新</option></select>\n'
            '<button type="button" class="ls-btn" id="ls-act" aria-pressed="false">只看活跃（45 天）</button>\n'
            '<button type="button" class="ls-btn" id="ls-reset">重置</button>\n'
            '</div>')


def render_chips(data, stats):
    out = ['<button type="button" class="ls-chip on" data-cat="all" aria-pressed="true">全部 <i>%d</i></button>'
           % stats['n']]
    for t in data['tracks']:
        cnt = len(stats['by_cat'].get(t['cat'], []))
        out.append('<button type="button" class="ls-chip" data-cat="%s" aria-pressed="false">%s <i>%d</i></button>'
                   % (esc_attr(t['cat']), esc(t['title']), cnt))
    return '\n'.join(out)


def render_section(data, stats):
    tracks = data['tracks']
    snapshot = data.get('snapshot', '')
    n = stats['n']
    total_wan = wan(stats['total'])

    # 赛道分布条形图
    bars = []
    ordered = sorted(tracks, key=lambda t: -sum(p['stars'] for p in stats['by_cat'].get(t['cat'], [])))
    max_track_title = ordered[0]['title'] if ordered else ''
    for t in ordered:
        items = stats['by_cat'].get(t['cat'], [])
        s = sum(p['stars'] for p in items)
        width = max(2.0, 100.0 * s / stats['max_track_stars']) if stats['max_track_stars'] else 2.0
        bars.append('<div class="ls-bar-row"><span class="ls-bar-name">%s <span>%d 个</span></span>'
                    '<span class="ls-bar-track"><span class="ls-bar-fill" style="width:%.1f%%"></span></span>'
                    '<span class="ls-bar-val">%s</span></div>'
                    % (esc(t['title']), len(items), width, wan(s)))

    # 星标前 12
    top = sorted(data['projects'], key=lambda p: -p['stars'])[:12]
    track_title = {t['cat']: t['title'] for t in tracks}
    top_rows = []
    for i, p in enumerate(top, 1):
        top_rows.append('<tr><td style="text-align:right;">%d</td><td><a href="%s" target="_blank" rel="noopener noreferrer">%s</a></td>'
                        '<td style="text-align:right;">%s</td><td>%s</td><td>%s</td><td>%s</td></tr>'
                        % (i, esc_attr(p['url']), esc(p['name']), intcomma(p['stars']),
                           esc(track_title.get(p['cat'], p['cat'])), esc(p['diff']),
                           esc(STATUS_LABEL.get(p['status'], p['status']))))

    langs = ' · '.join('%s %d' % (esc(k), v) for k, v in stats['langs'].most_common())
    created = ' · '.join('%s 年 %d' % (k, v) for k, v in sorted(stats['created'].items()))


    # 场景表
    scenarios = [
        ('个人终端提效', 'DeepSeek Harness 或 OpenCode（装完能跑）', 'cc-switch（多 CLI 统一入口）+ 低门槛技能包',
         '别一上来装五套；先记录一个真实任务的步数、token 和失败点'),
        ('IDE 内编码', 'Cline / Kilo Code / Continue（VS Code 内审批每步）', 'Roo-Code 的多模式提示词作参考；mini-swe-agent 读源码',
         '插件形态依赖各家 API Key，权限范围要按仓库收紧'),
        ('团队并行编码', 'Orca（复用已有订阅跑多 bot）或 OpenHands（沙箱跑全流程）', 'claude-task-master 做任务 DAG；SWE-agent 做评测基线',
         '并行任务必须共享同一套验证命令，否则无法比较产出'),
        ('企业内部平台', 'Dify（可视化 + 私有化）或 Coze Studio（插件/工作流齐全）', 'LangGraph 写复杂状态流转；n8n 做系统集成',
         '平台解决搭起来，框架解决改得动；两个都要，别只买一个'),
        ('知识与研究', 'RAGFlow / LightRAG（检索底座）', 'deer-flow、GPT-Researcher（调研产出）；graphify、graphiti（关系与时效）',
         '先定评测集再换方案，否则永远在换 embedding'),
        ('浏览器与桌面自动化', 'browser-use、Playwright MCP（浏览器）', 'midscene / UI-TARS / Agent-S（桌面与 GUI）',
         '登录态、验证码、页面改版是最常见的稳定性来源'),
        ('上线前评测与观测', 'Langfuse（追踪）或 promptfoo（CI 断言）', 'DeepEval、inspect_ai（可审计评测）；AgentOps 做回归',
         '评测要能进 CI；只看榜单分数会把配置差异当模型差异'),
        ('数据不出内网', 'OpenHands / Cline 自托管 + 本地模型', 'vLLM 或 SGLang 起模型服务；Continue 接自有网关',
         '先确认许可证：AGPL、Sustainable Use、闭源分发这几种要单独过法务'),
    ]
    scen_rows = '\n'.join('<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % row for row in scenarios)

    # 章节映射
    mapping = [
        ('DOC 03 AI Harness 企业落地教程', '编排框架 / SDK · 技能包 · Agent 基础设施', 'smolagents（最小实现）、LangGraph（状态机）、E2B（沙箱）'),
        ('DOC 17 Harness 横向对比与最新实现范式', '编码 Agent · 编排框架', 'mini-swe-agent（100 行读源码）、DeepSeek Harness、OpenCode'),
        ('DOC 18 Coze / Dify / LangChain 选型', '低代码平台 · 编排框架', 'Dify、Coze Studio、n8n、LangGraph'),
        ('DOC 12 AI Native 研发范式', '技能包 · 记忆层 · 评测', 'superpowers、mem0、Langfuse'),
        ('DOC 05 AI Infra 企业平台教程', 'Agent 基础设施 · Agentic RL', 'E2B、verl、slime'),
        ('DOC 13–15 岗位与面试', 'Agent 可观测 / 评测 · Agentic RL', 'promptfoo、inspect_ai、OpenEnv'),
        ('DOC 19 FastAPI × MCP × React', '工具协议 / MCP', 'FastMCP、python-sdk、A2A'),
        ('DOC 25 最新资料与来源索引', '教程 / 学习资料', 'hello-agents、ai-agents-for-beginners、learn-claude-code'),
    ]
    map_rows = '\n'.join('<tr><td>%s</td><td>%s</td><td>%s</td></tr>' % row for row in mapping)

    toc = [
        ('doc-26-1', '1. 这一章解决什么问题'),
        ('doc-26-2', '2. 数据与方法：137 条是怎么来的'),
        ('doc-26-3', '3. 一眼看全：137 个项目怎么分布'),
        ('doc-26-4', '4. 六条判断'),
        ('doc-26-5', '5. 按场景选型：八张组合牌'),
        ('doc-26-6', '6. 全量清单（可搜索 / 筛选 / 排序）'),
        ('doc-26-7', '7. 与本书章节的映射'),
        ('doc-26-8', '8. 从 30 分钟到 1 天的上手路径'),
        ('doc-26-9', '9. 数据维护与更新'),
        ('doc-26-10', '10. 来源与免责'),
    ]
    toc_html = '\n'.join('<li><a href="#%s">%s</a></li>' % (a, esc(t)) for a, t in toc)

    return """<!-- LANDSCAPE:SECTION:BEGIN -->
<section class="doc" id="doc-26" data-title="附录：GitHub Agent 全景图与选型指南（{n} 项目 × {nt} 赛道）"><header class="doc-head"><div class="doc-kicker">DOC 27</div><h2>附录：GitHub Agent 全景图与选型指南</h2><div class="doc-source">来源：27_GitHub_Agent全景图与选型指南.md · 数据快照 {snapshot}</div></header><details class="doc-toc"><summary>本篇目录</summary><div class="toc">
<ul>
{toc}
</ul>
</div>
</details><div class="doc-content"><blockquote>
<p>本章的数据与清单同步自开源项目 <a href="https://xiaowang018.github.io/agent-landscape/" target="_blank" rel="noopener noreferrer">GitHub Agent 项目全景图</a>（快照 <strong>{snapshot}</strong>）：<strong>{n}</strong> 个仓库、<strong>{nt}</strong> 个赛道、累计 <strong>{total}</strong>星标。元数据抓自 GitHub REST API，中文定位、适用人群与上手门槛为人工标注。</p>
</blockquote>
<h2 id="doc-26-1"><a class="hlink" href="#doc-26-1" title="本节链接">#</a>1. 这一章解决什么问题</h2>
<p>DOC 17（Harness 横向对比）用 11 个画像讲清了「一个 Harness 内部该怎么设计」，DOC 18 把 Coze / Dify / LangChain 放回各自的位置；但真正开始选型时，第一个问题还要更靠前一步：<strong>到底该从哪个仓库开始看？</strong></p>
<p>本章把 GitHub 上 Agent 相关的 {n} 个项目按 {nt} 个赛道摊开：给一份可搜索、可筛选的全量清单，给按场景的组合建议，并把每个赛道映射回本手册的对应章节。它是<strong>附录</strong>——正文给判断框架，附录给项目坐标：先用正文判断「我要的是哪一类能力」，再用本章找到这类能力里值得先装、先读源码的那两三个仓库。</p>
<table>
<thead>
<tr>
<th>文档</th>
<th>回答的问题</th>
<th>什么时候看</th>
</tr>
</thead>
<tbody>
<tr><td>DOC 17 Harness 横向对比</td><td>一个 Harness 内部该怎么设计（薄 Loop、WAL、Fail Fast、外部验证）</td><td>决定自研或改造 Harness 时</td></tr>
<tr><td>DOC 18 Coze / Dify / LangChain</td><td>平台、框架、代码三者边界在哪</td><td>决定「买平台还是写代码」时</td></tr>
<tr><td><strong>DOC 27（本章）</strong></td><td>{n} 个项目的坐标、赛道热度与上手门槛</td><td>决定「先看哪个仓库」时</td></tr>
</tbody>
</table>
<blockquote>
<p><strong>放置说明</strong>：本章编号 DOC 27、锚点 <code>doc-26</code>，追加在修订记录之后，是为了不移动 <code>doc-00</code>～<code>doc-25</code> 的既有锚点（见修订记录第 4 节「锚点稳定」约定）。</p>
</blockquote>
<h2 id="doc-26-2"><a class="hlink" href="#doc-26-2" title="本节链接">#</a>2. 数据与方法：137 条是怎么来的</h2>
<p>一张「项目地图」最容易失效的地方不是缺项目，而是口径不清：星数什么时候抓的、门槛谁定的、归档的算不算。先把口径写死。</p>
<table>
<thead>
<tr>
<th>字段</th>
<th>来源</th>
<th>说明</th>
</tr>
</thead>
<tbody>
<tr><td>星标、Fork、语言、许可证、最后提交时间、是否归档、创建时间</td><td>GitHub REST API <code>/repos/{{owner}}/{{repo}}</code></td><td>机器抓取，不是人工录入；会随时间变化</td></tr>
<tr><td>赛道、中文定位、适用人群、点评、上手门槛</td><td>人工标注</td><td>主观判断，可讨论；同一项目可能跨赛道</td></tr>
</tbody>
</table>
<p>维护状态按 GitHub 数据自动判定，<strong>归档优先于提交日期</strong>（刚归档的仓库最后一次提交也可能很近）：</p>
<ul>
<li><strong>已归档</strong>（{n_archived} 个）：仓库只读停更，不建议作为新项目选型；</li>
<li><strong>活跃</strong>（{n_active} 个）：45 天内有提交；</li>
<li><strong>维护中</strong>（{n_maintained} 个）：210 天内有提交；</li>
<li><strong>沉寂</strong>（{n_stale} 个）：超过 210 天无提交，同样不建议作为新项目选型。</li>
</ul>
<p>上手门槛按「装完能不能直接跑」分三档：<strong>易</strong>（{d_easy} 个，装完能跑）、<strong>中</strong>（{d_medium} 个，要读文档改代码）、<strong>难</strong>（{d_hard} 个，要理解架构或研究背景）。「教程 / 学习资料」赛道里的门槛指<strong>阅读门槛</strong>：易＝零基础能读，中＝要会写代码，难＝要懂架构。</p>
<p>许可证要单独说：{n} 个项目里只有 {std_lic} 个是纯 MIT / Apache-2.0，剩下 {nonstd_lic} 个带附加条款——NOASSERTION、Sustainable Use、AGPL-3.0、MIT + 企业版、闭源分发等。<strong>星标高不等于能商用</strong>，落地前逐条读 LICENSE；DOC 20「企业上线红线」同样适用。</p>
<p>收录边界也很明确：<strong>只收 Agent</strong>——纯 LLM 应用框架、模型推理框架、聊天客户端不在内，判断标准是「这东西能不能自己决定下一步做什么」。技能包与教程两个赛道是例外：它们不做决策，但选型时绕不过去，所以单独成赛道。</p>
<p>已知局限：星数受传播效应影响，不等于工程质量；人工标注有主观性；快照不是实时数据（更新方法见第 9 节）；「活跃」只说明 45 天内有提交，不说明它没有回归。</p>
<h2 id="doc-26-3"><a class="hlink" href="#doc-26-3" title="本节链接">#</a>3. 一眼看全：137 个项目怎么分布</h2>
<div class="ls-stats">
<div class="ls-stat"><b>{n}</b><span>收录项目</span></div>
<div class="ls-stat"><b>{nt}</b><span>赛道分类</span></div>
<div class="ls-stat"><b>{total}</b><span>累计星标</span></div>
<div class="ls-stat"><b>{n_active}</b><span>近 45 天有提交</span></div>
</div>
<p>星标不是均匀分布在 {nt} 个赛道里的。下面按赛道总星标排序；条形长度是相对最高赛道（{top_track}）的比例。</p>
<div class="ls-bars">
{bars}
</div>
<p>同一张图里能读出三件事：<strong>编码 Agent</strong> 数量与编排框架相同（都是 21 个），但星标是后者的 2.2 倍——热度和钱都在「能直接干活的成品」上；<strong>技能包</strong>只有 4 个项目却排到第 4，说明「怎么让 Agent 按规矩干活」已经独立成层；<strong>编排框架</strong>数量最多（21 个、{framework_stars}星），但已从「入口」退成「零件」。</p>
<p>星标的集中度同样值得警惕：前 20 名占全部星标的 {top20_share:.1f}%，前 10 名占 {top10_share:.1f}%，而中位数只有 {median}。<strong>榜单头部讲的是传播故事，中位数才是这个生态的常态。</strong></p>
<table>
<thead>
<tr>
<th style="text-align: right;">#</th>
<th>项目</th>
<th style="text-align: right;">星标</th>
<th>赛道</th>
<th>门槛</th>
<th>状态</th>
</tr>
</thead>
<tbody>
{top_rows}
</tbody>
</table>
<p>其余分布：</p>
<table>
<thead>
<tr><th>维度</th><th>分布</th></tr>
</thead>
<tbody>
<tr><td>语言</td><td>{langs}</td></tr>
<tr><td>门槛</td><td>易 {d_easy} · 中 {d_medium} · 难 {d_hard}</td></tr>
<tr><td>创建年份</td><td>{created}</td></tr>
</tbody>
</table>
<p>语言这一行有个反直觉的地方：Python 项目最多（{py} 个），但编码 Agent 的头部几乎全在 TypeScript / Rust——终端 TUI、沙箱、权限这些工程部件需要的是分发与进程控制，不是训练生态。Python 主导的是训练、评测和研究侧。</p>
<p>另外，{new_2y} 个项目（{new_share:.0f}%）创建于 2025–2026 年。<strong>这个赛道一年半就换了一茬</strong>，所以选型时「最近一次提交」比「星数」更能说明它还活着。</p>
<h2 id="doc-26-4"><a class="hlink" href="#doc-26-4" title="本节链接">#</a>4. 六条判断</h2>
<h3>判断一：入口从「自己搭」变成「装完直接用」</h3>
<p>星标前八里有六个是成品 Agent / Harness（rea、OpenClaw、ECC、DeepSeek Harness、Hermes、OpenCode），传统框架 LangChain 排到第 16。这不是说框架没用了，而是<strong>默认入口变了</strong>：如果目标是把事做完，先装一个成品；如果目标是做成产品，再回到框架层。</p>
<h3>判断二：技能包成了独立的一层</h3>
<p>4 个技能包合计 {skills_stars}星（占全榜 {skills_share:.1f}%），mattpocock/skills 与 obra/superpowers 都在 32 万以上，比绝大多数框架高。它们不写代码，写的是「Agent 该怎么干活」的纪律：先对齐意图、按 SDLC 走完、每步留证据。实践里更常见的做法是<strong>挑一两个混用</strong>而不是全装——技能太多会挤占上下文，还会互相抢命令名。</p>
<h3>判断三：框架没有消失，而是下沉成「被组合的零件」</h3>
<p>LangGraph 用「图 + 状态」把长流程、人审、断点续跑讲清楚，因此被大量产品当作状态机内核；Dify / Coze 这类平台则把框架包进可视化层。选型问题已经从「选哪个框架」变成「<strong>哪一层自己写、哪一层买</strong>」。</p>
<h3>判断四：「接线层」补齐了，它决定能不能上生产</h3>
<p>MCP 9 个项目 {protocol_stars}星、记忆层 7 个 {memory_stars}星、评测 6 个 {eval_stars}星；A2A 补上了 MCP 没管的另一半——Agent 之间怎么发现彼此、怎么委派任务。这一层做不出 Demo 效果，但少了它，前面装的东西都只能停在演示阶段。</p>
<h3>判断五：训练层出现，Agentic RL 从论文走进仓库</h3>
<p>verl、slime、prime-rl、ART、OpenEnv 五个项目组成新赛道。研究重心明显从「怎么调提示词」挪到「怎么造可验证的环境和 verifier」。对工程团队的实际含义是：<strong>跑通的流程可以考虑固化成小模型</strong>，把每次推理的钱省下来——但前提是先把评测基线做出来（见第 5 节「上线前评测」）。</p>
<h3>判断六：星数通胀与许可证风险并存</h3>
<p>前 20 名占 {top20_share:.1f}% 星，中位数只有 {median}；{nonstd_lic} 个项目带非标准许可；{n_archived} 个已归档、{n_stale} 个沉寂。三条合一：<strong>星标是传播指标，不是可用性指标</strong>。选型时先过三关——许可证、维护状态、有没有可复现的评测。</p>
<h2 id="doc-26-5"><a class="hlink" href="#doc-26-5" title="本节链接">#</a>5. 按场景选型：八张组合牌</h2>
<p>不要把「赛道第一」当成「我的第一」。下面按真实场景给组合：一列是<strong>先装哪个</strong>（当天能跑起来的），一列是<strong>再加什么</strong>（跑通之后补的能力），最后一列是最容易踩的坑。</p>
<table>
<thead>
<tr><th>场景</th><th>先装一个</th><th>再加两个</th><th>注意什么</th></tr>
</thead>
<tbody>
{scen_rows}
</tbody>
</table>
<p><strong>三条不要</strong>：</p>
<ol>
<li><strong>不要因为星数高就选它</strong>——先看它是否归档、许可证是否能过法务、issue 区最近三个月是否还在回。</li>
<li><strong>不要一开始就上多 Agent</strong>——榜单里 6 个多智能体项目合计 {multi_stars}星，但「通信即复杂度」；单 Agent 能解决的，加协作只会把失败点转移到调度层（DOC 17 铁律 6）。</li>
<li><strong>不要拿别人的 Benchmark 当自己的结论</strong>——同一模型换一套工具和提示，SWE-bench 分数可以差出十几个点；用自己的任务集复测，哪怕只有 20 条。</li>
</ol>
<h2 id="doc-26-6"><a class="hlink" href="#doc-26-6" title="本节链接">#</a>6. 全量清单（可搜索 / 筛选 / 排序）</h2>
<p>下面是本章的全量数据。<strong>搜索</strong>匹配仓库名、中文定位、适合人群、点评和 GitHub topics，空格分词表示「都要命中」；<strong>赛道</strong>只看某一类；<strong>语言 / 门槛</strong>按元数据过滤；<strong>只看活跃</strong>把 45 天内无提交的项目挡掉；<strong>排序</strong>只影响组内顺序。筛完后赛道标题右侧的项目数与星标会按当前可见项目重算。</p>
<p>这张清单也单独做成了一个页面：<a href="landscape.html" target="_blank" rel="noopener noreferrer">打开独立浏览页</a>——加载更快，筛选条件会写进地址栏，可以直接把链接发给同事。</p>
<div class="ls" id="agent-landscape">
{toolbar}
<div class="ls-chips" role="group" aria-label="按赛道筛选">
{chips}
</div>
<p class="ls-count" id="ls-count">显示 <b>{n}</b> / {n} 个项目 · {nt} 个赛道</p>
<div class="ls-groups">
{cards}
</div>
<p class="ls-empty ls-hidden" id="ls-empty">没有匹配的项目。换个关键词，或点「重置」回到全量。</p>
</div>
<h2 id="doc-26-7"><a class="hlink" href="#doc-26-7" title="本节链接">#</a>7. 与本书章节的映射</h2>
<p>读到某一章卡住时，从这张表倒查该看哪些仓库：</p>
<table>
<thead>
<tr><th>本手册章节</th><th>对应赛道</th><th>建议先看的项目</th></tr>
</thead>
<tbody>
{map_rows}
</tbody>
</table>
<h2 id="doc-26-8"><a class="hlink" href="#doc-26-8" title="本节链接">#</a>8. 从 30 分钟到 1 天的上手路径</h2>
<ol>
<li><strong>30 分钟：装并跑通一个成品。</strong>DeepSeek Harness 或 OpenCode 二选一，用一个真实的小任务（改一个 bug、补一个测试），记录步数、token、失败点各一次。目的不是学会它，而是建立「成品 Harness 已经能做什么」的基线。</li>
<li><strong>2 小时：读最小的实现。</strong>mini-swe-agent（约 100 行）和 smolagents（核心约千行）各读一遍，重点看三件事：循环怎么退出、工具返回错误怎么进上下文、什么时候停下来问人。这一层读完，DOC 17 的八条铁律才有落点。</li>
<li><strong>1 天：做一个对照实验。</strong>同一个任务，用「成品」和「框架」各实现一次（例如 OpenCode vs LangGraph），比较：完成率、步数、token、人工介入次数、失败可复现性。结论写成一页，参照 DOC 24 的验收格式存档。</li>
</ol>
<p>验收清单（做完打勾）：</p>
<ul>
<li>能说清你选的方案在「<strong>薄 Loop / 厚 Control Plane</strong>」里的位置；</li>
<li>工具调用有超时、幂等和权限边界，失败会进日志而不是被模型忽略；</li>
<li>有外部验证（编译 / 测试 / 类型检查），不是模型自评；</li>
<li>知道崩溃后从哪里恢复（WAL 或等价机制）；</li>
<li>评测集是你自己的 20 条任务，不是榜单分数。</li>
</ul>
<h2 id="doc-26-9"><a class="hlink" href="#doc-26-9" title="本节链接">#</a>9. 数据维护与更新</h2>
<p>本章的清单不是手写 HTML，而是由脚本从数据文件生成的。数据文件：<code>docs/data/agent-landscape-{snapshot}.json</code>；生成器：<code>scripts/build_landscape.py</code>；合并器：<code>scripts/merge_landscape_data.py</code>。</p>
<pre><code># 1. 在上游仓库刷新元数据（需要 GitHub token，未认证只有 60 次/小时）
git clone https://github.com/xiaowang018/agent-landscape
cd agent-landscape &amp;&amp; GITHUB_TOKEN=xxx python scripts/fetch.py

# 2. 合并成快照（data.json + annotations.json + tracks.json → 单文件）
python scripts/merge_landscape_data.py --src ../agent-landscape --date 2026-11-24

# 3. 生成并写入 index.html（只替换 LANDSCAPE 标记块，可重复执行）
python scripts/build_landscape.py --apply

# 4. 校验：卡片数、锚点、导航一致性
python scripts/build_landscape.py --check</code></pre>
<p>更新约定：</p>
<ol>
<li><strong>先改数据、再改结论</strong>：星数、归档状态、赛道归属变化后，第 3、4 节的数字和判断要一起复核；</li>
<li><strong>不要手改卡片</strong>：<code>--apply</code> 会覆盖标记块内的内容，手改会在下次生成时丢失；</li>
<li><strong>快照命名</strong>：数据文件按抓取日期命名（<code>agent-landscape-YYYY-MM-DD.json</code>），脚本默认取字典序最后一个；换快照时同步改本章 <code>doc-source</code> 与修订记录；</li>
<li><strong>上游署名</strong>：数据整理自 agent-landscape 项目，更新时保留其来源链接与许可证说明；</li>
<li><strong>新增项目先补标注</strong>：上游 <code>annotations.json</code> 里缺标注的仓库会被合并脚本拒绝（避免页面少卡或字段空白），补完标注再合并。</li>
</ol>
<h2 id="doc-26-10"><a class="hlink" href="#doc-26-10" title="本节链接">#</a>10. 来源与免责</h2>
<ul>
<li>上游项目：<a href="https://github.com/xiaowang018/agent-landscape" target="_blank" rel="noopener noreferrer">xiaowang018/agent-landscape</a>；在线版：<a href="https://xiaowang018.github.io/agent-landscape/" target="_blank" rel="noopener noreferrer">xiaowang018.github.io/agent-landscape</a>；</li>
<li>元数据：GitHub REST API（快照 {snapshot}）；中文标注与门槛：上游人工标注；</li>
<li>本章只整理公开信息与公开元数据，各项目的版权与许可证归其原作者；标注为「见仓库」「NOASSERTION」的，请以仓库 LICENSE 文件为准；</li>
<li>数据会过时：做采购或架构决策前，请用当日数据复核，并按 DOC 20 的上线红线逐项检查。</li>
</ul>
</div></section>
<!-- LANDSCAPE:SECTION:END -->""".format(
        n=n,
        nt=stats['n_tracks'],
        total=total_wan,
        snapshot=snapshot,
        toc=toc_html,
        n_archived=stats['status'].get('archived', 0),
        n_active=stats['status'].get('active', 0),
        n_maintained=stats['status'].get('maintained', 0),
        n_stale=stats['status'].get('stale', 0),
        d_easy=stats['diff'].get('易', 0),
        d_medium=stats['diff'].get('中', 0),
        d_hard=stats['diff'].get('难', 0),
        std_lic=stats['standard_lic'],
        nonstd_lic=stats['nonstd_lic'],
        bars='\n'.join(bars),
        top_rows='\n'.join(top_rows),
        langs=langs,
        created=created,
        py=stats['langs'].get('Python', 0),
        top20_share=stats['top20_share'],
        top10_share=stats['top10_share'],
        median=intcomma(stats['median']),
        new_2y=stats['new_2y'],
        new_share=100.0 * stats['new_2y'] / n,
        top_track=max_track_title,
        framework_stars=wan(sum(p['stars'] for p in stats['by_cat'].get('framework', []))),
        skills_stars=wan(sum(p['stars'] for p in stats['by_cat'].get('skills', []))),
        skills_share=100.0 * sum(p['stars'] for p in stats['by_cat'].get('skills', [])) / stats['total'],
        protocol_stars=wan(sum(p['stars'] for p in stats['by_cat'].get('protocol', []))),
        memory_stars=wan(sum(p['stars'] for p in stats['by_cat'].get('memory', []))),
        eval_stars=wan(sum(p['stars'] for p in stats['by_cat'].get('eval', []))),
        multi_stars=wan(sum(p['stars'] for p in stats['by_cat'].get('multi', []))),
        scen_rows=scen_rows,
        map_rows=map_rows,
        lang_options=''.join('<option value="%s">%s（%d）</option>'
                             % (esc_attr(k), esc(k), v) for k, v in stats['langs'].most_common()),
        chips=render_chips(data, stats),
        toolbar=render_toolbar(stats),
        cards=render_cards(data, stats),
    )


# --------------------------------------------------------------------------- #
# standalone page (landscape.html)
# --------------------------------------------------------------------------- #
WIDGET_CSS = CSS.split('/* LANDSCAPE:CSS:BEGIN */', 1)[1].rsplit('/* LANDSCAPE:CSS:END */', 1)[0].strip('\n')
JS_BODY = JS.split('<script>', 1)[1].rsplit('</script>', 1)[0].strip('\n')

SHELL_CSS = r""":root{--bg:#f5f7fb;--panel:#fff;--panel2:#eef3f8;--ink:#17212b;--muted:#607080;--line:#d8e0e8;--accent:#0b5fa5;--accent2:#0b7a75;--shadow:0 14px 38px rgba(24,52,82,.09)}
html[data-theme="dark"]{--bg:#0f141b;--panel:#151d26;--panel2:#1d2834;--ink:#e9f0f6;--muted:#9caaba;--line:#2b3948;--accent:#65b9ef;--accent2:#57d2c8;--shadow:0 18px 44px rgba(0,0,0,.35)}
*{box-sizing:border-box} html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font-family:"Segoe UI","Microsoft YaHei",system-ui,sans-serif;line-height:1.7}
a{color:var(--accent);text-decoration:none} a:hover{text-decoration:underline}
.wrap{max-width:1400px;margin:0 auto;padding:24px 22px 48px}
.page-head{background:linear-gradient(135deg,color-mix(in srgb,var(--accent) 13%,var(--panel)),var(--panel));border:1px solid var(--line);border-radius:22px;padding:26px 28px;box-shadow:var(--shadow);margin-bottom:14px}
.head-top{display:flex;gap:18px;justify-content:space-between;align-items:flex-start;flex-wrap:wrap}
.kicker{font-size:11px;letter-spacing:.16em;color:var(--accent);font-weight:700;margin-bottom:8px}
.page-head h1{margin:0 0 10px;font-size:clamp(22px,3vw,34px);line-height:1.25}
.page-head h1 em{font-style:normal;color:var(--accent)}
.lede{margin:0;max-width:840px;font-size:14px;color:var(--muted)}
.head-actions{display:flex;gap:8px;flex-wrap:wrap}
.head-actions a,.head-actions button{padding:7px 13px;border:1px solid var(--line);border-radius:999px;background:var(--panel);color:var(--ink);font:inherit;font-size:13px;cursor:pointer}
.head-actions a:hover,.head-actions button:hover{border-color:var(--accent);color:var(--accent);text-decoration:none}
.ls-toolbar{position:sticky;top:0;z-index:30;padding:10px 0 2px;background:color-mix(in srgb,var(--bg) 94%,transparent);backdrop-filter:blur(10px);border-bottom:1px solid var(--line);margin-bottom:6px}
.page-foot{margin-top:30px;padding-top:14px;border-top:1px solid var(--line);color:var(--muted);font-size:12.5px;display:flex;gap:10px 20px;flex-wrap:wrap;justify-content:space-between}
@media (max-width:1000px){.wrap{padding:14px 14px 36px}.page-head{padding:20px 18px}}
@media print{.ls-toolbar,.head-actions{display:none!important}.ls-card{break-inside:avoid}}
"""


def render_standalone(data, stats):
    snapshot = data.get('snapshot', '')
    return """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GitHub Agent 全景图 · {n} 个项目 × {nt} 个赛道 · 快照 {snapshot}</title>
<meta name="description" content="GitHub 上 Agent 相关项目的赛道全景：{n} 个项目、{nt} 个赛道、累计星标 {total}（快照 {snapshot}）。支持搜索、按赛道/语言/门槛/活跃度筛选，筛选状态写进地址栏。">
<style>
{shell_css}
{widget_css}
</style>
</head>
<body>
<div class="wrap">
<header class="page-head">
<div class="head-top">
<div>
<div class="kicker">GitHub Agent Landscape · 数据快照 {snapshot}</div>
<h1>Agent 项目全景图：<em>{n} 个项目 · {nt} 个赛道</em></h1>
<p class="lede">把 GitHub 上 Agent 相关的项目按赛道摊开，用来回答「想搭一个 Agent，该从哪个仓库开始看」。搜索匹配仓库名、中文定位、适合人群、点评和 GitHub topics（空格分词表示都要命中）；筛选条件会写进地址栏，可以直接把链接发给同事。数据来自 <a href="https://xiaowang018.github.io/agent-landscape/" target="_blank" rel="noopener noreferrer">GitHub Agent 项目全景图</a>，元数据抓自 GitHub REST API，中文定位与门槛为上游人工标注。</p>
</div>
<div class="head-actions">
<button type="button" id="ls-theme">切换夜间</button>
<a href="index.html#doc-26">返回手册 DOC 27</a>
<a href="https://github.com/xiaowang018/agent-landscape" target="_blank" rel="noopener noreferrer">上游仓库</a>
</div>
</div>
<div class="ls-stats">
<div class="ls-stat"><b>{n}</b><span>收录项目</span></div>
<div class="ls-stat"><b>{nt}</b><span>赛道分类</span></div>
<div class="ls-stat"><b>{total}</b><span>累计星标</span></div>
<div class="ls-stat"><b>{n_active}</b><span>近 45 天有提交</span></div>
</div>
</header>
<div class="ls-toolbar">
{toolbar}
<div class="ls-chips" role="group" aria-label="按赛道筛选">
{chips}
</div>
<p class="ls-count" id="ls-count">显示 <b>{n}</b> / {n} 个项目 · {nt} 个赛道</p>
</div>
<div class="ls" id="agent-landscape" data-hash="1">
<div class="ls-groups">
{cards}
</div>
<p class="ls-empty ls-hidden" id="ls-empty">没有匹配的项目。换个关键词，或点「重置」回到全量。</p>
</div>
<footer class="page-foot">
<span>数据来自 <a href="https://github.com/xiaowang018/agent-landscape" target="_blank" rel="noopener noreferrer">xiaowang018/agent-landscape</a>（GitHub REST API 快照 {snapshot}）；中文定位、门槛与点评为上游人工标注；各项目版权与许可证归其原作者。</span>
<span>本页由 <code>scripts/build_landscape.py</code> 从 <code>docs/data/agent-landscape-{snapshot}.json</code> 生成，请勿手改。</span>
</footer>
</div>
<script>
{js_body}
</script>
</body>
</html>
""".format(
        n=stats['n'], nt=stats['n_tracks'], total=wan(stats['total']), snapshot=snapshot,
        n_active=stats['status'].get('active', 0),
        shell_css=SHELL_CSS, widget_css=WIDGET_CSS, js_body=JS_BODY,
        toolbar=render_toolbar(stats), chips=render_chips(data, stats),
        cards=render_cards(data, stats))


def render_nav(stats):
    links = [
        ('doc-26-1', '1. 这一章解决什么问题'),
        ('doc-26-2', '2. 数据与方法：137 条是怎么来的'),
        ('doc-26-3', '3. 一眼看全：137 个项目怎么分布'),
        ('doc-26-4', '4. 六条判断'),
        ('doc-26-5', '5. 按场景选型：八张组合牌'),
        ('doc-26-6', '6. 全量清单（可搜索 / 筛选 / 排序）'),
        ('doc-26-7', '7. 与本书章节的映射'),
        ('doc-26-8', '8. 从 30 分钟到 1 天的上手路径'),
        ('doc-26-9', '9. 数据维护与更新'),
        ('doc-26-10', '10. 来源与免责'),
    ]
    items = '\n'.join('<li><a href="#%s">%s</a></li>' % (a, esc(t)) for a, t in links)
    return ('<!-- LANDSCAPE:NAV:BEGIN -->\n'
            '<details class="nav-group"><summary class="nav-link" data-target="doc-26"><span class="nav-num">27</span>'
            '<span class="nav-title">附录：GitHub Agent 全景图与选型指南</span></summary>'
            '<div class="nav-sub"><a class="nav-jump" href="#doc-26">↑ 跳到本章开头</a><div class="toc">\n'
            '<ul>\n' + items + '\n</ul>\n</div>\n</div></details>\n'
            '<!-- LANDSCAPE:NAV:END -->')


# --------------------------------------------------------------------------- #
# apply / check
# --------------------------------------------------------------------------- #
def replace_block(text, begin, end, payload, anchor):
    if begin in text and end in text:
        start = text.index(begin)
        stop = text.index(end, start) + len(end)
        return text[:start] + payload + text[stop:]
    if anchor not in text:
        sys.exit('找不到插入锚点 %r，也不是二次运行（缺标记）' % anchor)
    return text.replace(anchor, payload + anchor, 1)


def build_all(data, stats):
    return {
        'CSS': (CSS, '/* LANDSCAPE:CSS:BEGIN */', '/* LANDSCAPE:CSS:END */', '</style>'),
        'NAV': (render_nav(stats), '<!-- LANDSCAPE:NAV:BEGIN -->', '<!-- LANDSCAPE:NAV:END -->', '</aside>'),
        'SECTION': (render_section(data, stats), '<!-- LANDSCAPE:SECTION:BEGIN -->', '<!-- LANDSCAPE:SECTION:END -->', '</main>'),
        'JS': (JS, '<!-- LANDSCAPE:JS:BEGIN -->', '<!-- LANDSCAPE:JS:END -->', '</body>'),
    }


def check(html_text, data):
    problems = []
    n = len(data['projects'])
    cards = html_text.count('<article class="ls-card"')
    if cards != n:
        problems.append('卡片数 %d != 数据条数 %d' % (cards, n))
    ids = re.findall(r'\sid="([^"]+)"', html_text)
    dup = [i for i, c in Counter(ids).items() if c > 1]
    if dup:
        problems.append('重复 id：%s' % ', '.join(dup[:10]))
    id_set = set(ids)
    hrefs = re.findall(r'href="#([^"]+)"', html_text)
    missing = sorted({h for h in hrefs if h not in id_set})
    if missing:
        problems.append('锚点缺失：%s' % ', '.join(missing[:10]))
    for marker in ('LANDSCAPE:CSS', 'LANDSCAPE:NAV', 'LANDSCAPE:SECTION', 'LANDSCAPE:JS'):
        if marker + ':BEGIN' not in html_text:
            problems.append('缺少标记 %s' % marker)
    if os.path.exists(STANDALONE):
        page = open(STANDALONE, encoding='utf-8').read()
        if page.count('<article class="ls-card"') != n:
            problems.append('landscape.html 卡片数不对')
        if '<script src' in page or '<link rel="stylesheet"' in page:
            problems.append('landscape.html 引用了外部资源（应保持单文件离线可用）')
        if 'data-hash="1"' not in page:
            problems.append('landscape.html 缺少地址栏状态开关')
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='写入 index.html')
    ap.add_argument('--check', action='store_true', help='只校验')
    ap.add_argument('--data', default=None, help='指定数据文件')
    args = ap.parse_args()

    data = load_data(args.data)
    stats = compute_stats(data)

    # 页面是 CRLF（Windows 检出）；保留原换行风格，避免整文件差异
    with open(INDEX, 'rb') as fb:
        raw = fb.read()
    crlf = raw.count(b'\r\n') > raw.count(b'\n') // 2

    with open(INDEX, encoding='utf-8') as f:
        html_text = f.read()

    if args.check:
        problems = check(html_text, data)
        if problems:
            print('CHECK FAILED')
            for p in problems:
                print(' -', p)
            return 1
        print('CHECK OK: %d 个项目 / %d 个赛道 / 卡片与锚点一致' % (stats['n'], stats['n_tracks']))
        return 0

    blocks = build_all(data, stats)
    for payload, begin, end, anchor in blocks.values():
        html_text = replace_block(html_text, begin, end, payload, anchor)

    problems = check(html_text, data)

    print('snapshot=%s projects=%d tracks=%d stars=%s active=%d'
          % (data['snapshot'], stats['n'], stats['n_tracks'], wan(stats['total']),
             stats['status'].get('active', 0)))
    print('section bytes=%d nav bytes=%d css bytes=%d js bytes=%d page bytes=%d'
          % (len(blocks['SECTION'][0]), len(blocks['NAV'][0]), len(CSS), len(JS), len(html_text)))
    if problems:
        print('CHECK FAILED')
        for p in problems:
            print(' -', p)
        return 1

    if args.apply:
        out = html_text.replace('\r\n', '\n')
        if crlf:
            out = out.replace('\n', '\r\n')
        with open(INDEX, 'w', encoding='utf-8', newline='') as f:
            f.write(out)
        standalone = render_standalone(data, stats)
        with open(STANDALONE, 'w', encoding='utf-8', newline='\n') as f:
            f.write(standalone)
        print('APPLIED ->', INDEX)
        print('WROTE ->', STANDALONE, len(standalone), 'chars')
    else:
        print('DRY RUN（加 --apply 才会写入）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
