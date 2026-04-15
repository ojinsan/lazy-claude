#!/usr/bin/env python3
import json
import sys
from pathlib import Path

sys.path.insert(0, "/home/lazywork/lazyboy/trade")

from _lib.api import get_price, get_volume_ratio, get_support_resistance
from _lib.wyckoff import analyze_wyckoff
from _lib.broker_profile import analyze_players

WATCH = Path('/home/lazywork/lazyboy/trade/watchlist/active.json')


def group_name(v: dict):
    layer = int(v.get('layer', 0) or 0)
    status = (v.get('status','') or '').lower()
    if layer >= 3 and status == 'ready':
        return 'G1_READY'
    if layer >= 3 and status == 'watching':
        return 'G2_WATCH_L3'
    if layer == 2:
        return 'G3_CONFIRM_L2'
    return 'G4_RESEARCH_L1'


def score(t):
    p = analyze_players(t)
    w = analyze_wyckoff(t)
    price = get_price(t)
    vr = get_volume_ratio(t)
    sr = get_support_resistance(t)
    support = float(getattr(sr,'support',0) or 0)
    resistance = float(getattr(sr,'resistance',0) or 0)

    s = 0
    why = []
    if w.phase == 'ACCUMULATION': s += 30; why.append('accumulation')
    elif w.phase == 'MARKUP': s += 15; why.append('markup')
    elif w.phase == 'MARKDOWN': s -= 8; why.append('markdown')
    elif w.phase == 'DISTRIBUTION': s -= 15; why.append('distribution')

    if w.smi_trend == 'RISING': s += 10; why.append('SMI rising')
    elif w.smi_trend == 'FALLING': s -= 8; why.append('SMI falling')

    if w.structure == 'HH-HL': s += 8; why.append('HH-HL')
    elif w.structure == 'LH-LL': s -= 6; why.append('LH-LL')

    cs = (p.conviction_signal or '').lower()
    if 'underwater' in cs: s += 12; why.append('underwater smart money')
    elif 'accumulating' in cs: s += 8; why.append('smart money accumulating')

    insight = p.key_insight or ''
    if 'distributing' in insight.lower() or 'distribution' in insight.lower():
        s -= 10; why.append('distribution signal')

    if p.trap_detected and p.trap_type == 'distribution_trap':
        s -= 15; why.append('distribution trap')

    if vr >= 2.0: s += 10; why.append(f'vol {vr:.1f}x')
    elif vr >= 1.3: s += 6; why.append(f'vol {vr:.1f}x')
    elif vr < 0.8: s -= 4; why.append(f'thin vol {vr:.1f}x')

    rr = 0
    if price > 0 and support > 0 and resistance > price and support < price:
        dn = (price-support)/price
        up = (resistance-price)/price
        rr = up/dn if dn > 0 else 0
        if rr >= 1.8: s += 8; why.append(f'RR {rr:.1f}')
        elif rr < 1.0: s -= 6; why.append(f'RR {rr:.1f}')

    return {
        'ticker': t,
        'score': round(s,2),
        'price': price,
        'phase': w.phase,
        'smi': w.smi_trend,
        'structure': w.structure,
        'volr': round(vr,2),
        'support': support,
        'resistance': resistance,
        'rr': round(rr,2),
        'insight': insight,
        'why': why[:6],
    }


def main():
    data = json.loads(WATCH.read_text())
    groups = {'G1_READY':[], 'G2_WATCH_L3':[], 'G3_CONFIRM_L2':[], 'G4_RESEARCH_L1':[]}

    for t,v in data.items():
        if t.startswith('_') or not isinstance(v, dict):
            continue
        g = group_name(v)
        groups[g].append(t)

    out = {'groups':{}}
    for g, tickers in groups.items():
        rows = []
        for t in tickers:
            try:
                rows.append(score(t))
            except Exception:
                continue
        rows.sort(key=lambda x: x['score'], reverse=True)
        out['groups'][g] = rows

    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
