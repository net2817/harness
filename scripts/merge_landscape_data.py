#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把上游 agent-landscape 的三份源文件合并成本手册用的单文件快照。

上游仓库：https://github.com/xiaowang018/agent-landscape
    data.json              GitHub REST API 抓到的元数据（星标、Fork、语言、许可证、最后提交…）
    scripts/annotations.json 人工标注：赛道、中文定位、适合人群、点评、门槛
    scripts/tracks.json    17 个赛道的顺序、标题与副标题

用法：
    python scripts/merge_landscape_data.py --src ../agent-landscape
    python scripts/merge_landscape_data.py --src ../agent-landscape --date 2026-11-24 --out docs/data/agent-landscape-2026-11-24.json

合并时会做四件事：
1. 校验 data.json 与 annotations.json 双向一一对应（缺一条就报错，避免页面少卡）；
2. 按「45 天 / 210 天 / 归档」规则算维护状态（归档优先于提交日期）；
3. 归一化文案：上游「适合：…的」结尾补「人」字，渲染成「适合…的人」，不改语义；
4. 按 tracks.json 的赛道顺序、星标降序排好，写成一个 JSON 快照。
"""

import argparse
import datetime
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def status_of(pushed, archived, today):
    if archived:
        return 'archived'
    if not pushed:
        return 'stale'
    days = (today - datetime.date.fromisoformat(pushed)).days
    if days <= 45:
        return 'active'
    if days <= 210:
        return 'maintained'
    return 'stale'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', required=True, help='agent-landscape 仓库根目录')
    ap.add_argument('--date', default=None, help='快照日期 YYYY-MM-DD，默认读 scripts/snapshot.json')
    ap.add_argument('--out', default=None, help='输出路径，默认 docs/data/agent-landscape-<date>.json')
    args = ap.parse_args()

    src = os.path.abspath(args.src)
    data_rows = read_json(os.path.join(src, 'data.json'))
    ann = read_json(os.path.join(src, 'scripts', 'annotations.json'))
    tracks = read_json(os.path.join(src, 'scripts', 'tracks.json'))

    if args.date:
        snapshot = args.date
    else:
        snapshot = read_json(os.path.join(src, 'scripts', 'snapshot.json'))['date']
    today = datetime.date.fromisoformat(snapshot)

    by_name = {r['full_name'].lower(): r for r in data_rows}
    missing_ann = [k for k in by_name if k not in ann]
    missing_data = [k for k in ann if k not in by_name]
    if missing_ann or missing_data:
        print('数据与标注不一致：')
        if missing_ann:
            print('  有仓库但缺标注：%s' % ', '.join(missing_ann[:10]))
        if missing_data:
            print('  有标注但缺仓库：%s' % ', '.join(missing_data[:10]))
        return 1

    order = [t['cat'] for t in tracks]
    unknown = sorted({a['cat'] for a in ann.values()} - set(order))
    if unknown:
        print('标注里的赛道没在 tracks.json 登记：%s' % ', '.join(unknown))
        return 1

    projects = []
    for key, a in ann.items():
        d = by_name[key]
        aud = a['aud'].strip()
        if aud.endswith('的'):
            aud += '人'
        pushed = d.get('pushed_at', '')
        archived = bool(d.get('archived', False))
        projects.append({
            'name': a['name'],
            'url': d.get('url') or ('https://github.com/' + a['name']),
            'homepage': d.get('homepage', ''),
            'cat': a['cat'],
            'pitch': a['pitch'],
            'aud': aud,
            'note': a['note'],
            'diff': a['diff'],
            'lic': a.get('lic', ''),
            'stars': d.get('stars', 0),
            'forks': d.get('forks', 0),
            'lang': d.get('lang', '-'),
            'pushed_at': pushed,
            'created_at': d.get('created_at', ''),
            'archived': archived,
            'status': status_of(pushed, archived, today),
            'topics': d.get('topics', []),
        })

    projects.sort(key=lambda p: (order.index(p['cat']), -p['stars'], p['name'].lower()))

    out = {
        'snapshot': snapshot,
        'source': 'https://xiaowang018.github.io/agent-landscape/',
        'source_repo': 'https://github.com/xiaowang018/agent-landscape',
        'license_note': '本文件只整理公开元数据（GitHub REST API）与人工标注；各项目版权与许可证归其原作者。',
        'status_rule': {
            'archived': '仓库已归档',
            'active': '45 天内有提交',
            'maintained': '210 天内有提交',
            'stale': '超过 210 天无提交',
        },
        'tracks': tracks,
        'projects': projects,
    }

    out_path = args.out or os.path.join(ROOT, 'docs', 'data', 'agent-landscape-%s.json' % snapshot)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    status = {}
    for p in projects:
        status[p['status']] = status.get(p['status'], 0) + 1
    print('wrote %s' % out_path)
    print('snapshot=%s projects=%d tracks=%d stars=%d %s'
          % (snapshot, len(projects), len(tracks), sum(p['stars'] for p in projects), status))
    return 0


if __name__ == '__main__':
    sys.exit(main())
