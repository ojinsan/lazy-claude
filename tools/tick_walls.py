#!/usr/bin/env python3

from __future__ import annotations


def analyze_tick_walls(orderbook: dict) -> dict:
    """Analyze nearest per-tick offer/bid walls and simple wall psychology heuristics."""
    bids = orderbook.get('bid', []) or []
    offers = orderbook.get('offer', []) or []
    out = {
        'nearest_offer_wall': None,
        'nearest_bid_wall': None,
        'offer_wall_concentration': 0.0,
        'bid_wall_concentration': 0.0,
        'retail_blocking_risk': 'low',
        'whale_accumulation_hint': 'unclear',
    }
    try:
        top_offers = offers[:5]
        top_bids = bids[:5]
        offer_vols = [float(x.get('volume', 0) or 0) for x in top_offers]
        bid_vols = [float(x.get('volume', 0) or 0) for x in top_bids]
        if offer_vols:
            max_offer = max(offer_vols)
            idx = offer_vols.index(max_offer)
            out['nearest_offer_wall'] = {
                'price': top_offers[idx].get('price'),
                'volume': max_offer,
                'tick_index': idx,
            }
            total_offer = sum(offer_vols)
            out['offer_wall_concentration'] = round(max_offer / total_offer, 3) if total_offer else 0.0
        if bid_vols:
            max_bid = max(bid_vols)
            idx = bid_vols.index(max_bid)
            out['nearest_bid_wall'] = {
                'price': top_bids[idx].get('price'),
                'volume': max_bid,
                'tick_index': idx,
            }
            total_bid = sum(bid_vols)
            out['bid_wall_concentration'] = round(max_bid / total_bid, 3) if total_bid else 0.0
        if out['nearest_offer_wall'] and out['nearest_offer_wall']['tick_index'] <= 1 and out['offer_wall_concentration'] >= 0.35:
            out['retail_blocking_risk'] = 'high'
        elif out['nearest_offer_wall'] and out['offer_wall_concentration'] >= 0.25:
            out['retail_blocking_risk'] = 'medium'
        if out['nearest_bid_wall'] and out['nearest_bid_wall']['tick_index'] <= 1 and out['bid_wall_concentration'] >= 0.35:
            out['whale_accumulation_hint'] = 'possible bid defense / accumulation'
    except Exception:
        pass
    return out



def compare_tick_walls(previous: dict | None, current: dict | None) -> dict:
    """Compare previous/current wall snapshots for lifecycle + price acceptance clues."""
    out = {
        'offer_wall_lifecycle': 'unknown',
        'bid_wall_lifecycle': 'unknown',
        'price_acceptance': 'unclear',
    }
    if not previous or not current:
        return out
    prev_offer = previous.get('nearest_offer_wall') or {}
    curr_offer = current.get('nearest_offer_wall') or {}
    prev_bid = previous.get('nearest_bid_wall') or {}
    curr_bid = current.get('nearest_bid_wall') or {}

    try:
        pv = float(prev_offer.get('volume') or 0)
        cv = float(curr_offer.get('volume') or 0)
        if pv and not cv:
            out['offer_wall_lifecycle'] = 'vanished'
        elif pv and cv and cv < pv * 0.7:
            out['offer_wall_lifecycle'] = 'shrinking'
        elif pv and cv and cv > pv * 1.2:
            out['offer_wall_lifecycle'] = 'refreshing'
    except Exception:
        pass

    try:
        pv = float(prev_bid.get('volume') or 0)
        cv = float(curr_bid.get('volume') or 0)
        if pv and not cv:
            out['bid_wall_lifecycle'] = 'vanished'
        elif pv and cv and cv < pv * 0.7:
            out['bid_wall_lifecycle'] = 'shrinking'
        elif pv and cv and cv > pv * 1.2:
            out['bid_wall_lifecycle'] = 'refreshing'
    except Exception:
        pass

    try:
        prev_offer_price = float(prev_offer.get('price') or 0)
        curr_bid_price = float(curr_bid.get('price') or 0)
        if out['offer_wall_lifecycle'] in {'shrinking', 'vanished'} and curr_bid_price >= prev_offer_price:
            out['price_acceptance'] = 'accepted above prior offer wall'
        elif out['offer_wall_lifecycle'] in {'shrinking', 'vanished'}:
            out['price_acceptance'] = 'wall changed but no acceptance yet'
    except Exception:
        pass

    return out



def compare_wall_series(history: list[dict]) -> dict:
    """Compare a small series of wall snapshots for stronger lifecycle inference."""
    out = {
        'offer_trend': 'unclear',
        'bid_trend': 'unclear',
        'acceptance_trend': 'unclear',
    }
    if len(history) < 2:
        return out
    offers = [float((x.get('nearest_offer_wall') or {}).get('volume') or 0) for x in history]
    bids = [float((x.get('nearest_bid_wall') or {}).get('volume') or 0) for x in history]
    prices = [float((x.get('nearest_bid_wall') or {}).get('price') or 0) for x in history]
    if len(offers) >= 3 and offers[0] > offers[-1] and all(offers[i] >= offers[i+1] for i in range(len(offers)-1)):
        out['offer_trend'] = 'steady shrinking'
    elif len(offers) >= 3 and offers[-1] > offers[0] and any(offers[i+1] > offers[i] for i in range(len(offers)-1)):
        out['offer_trend'] = 'reloading / refreshing'
    if len(bids) >= 3 and bids[-1] > bids[0] and any(bids[i+1] > bids[i] for i in range(len(bids)-1)):
        out['bid_trend'] = 'bid support strengthening'
    elif len(bids) >= 3 and bids[-1] < bids[0] and any(bids[i+1] < bids[i] for i in range(len(bids)-1)):
        out['bid_trend'] = 'bid support weakening'
    if len(prices) >= 3 and prices[-1] > prices[0]:
        out['acceptance_trend'] = 'price stepping up'
    return out
