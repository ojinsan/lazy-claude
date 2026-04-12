#!/usr/bin/env python3
import os, json, argparse, requests
from pathlib import Path

ENV_PATH = Path('/home/lazywork/workspace/.env.local')
BATCH_LIMIT = 10


def load_env():
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            os.environ.setdefault(k, v)


def api_headers(json_mode=True):
    pat = os.environ['AIRTABLE_PAT']
    headers = {'Authorization': f'Bearer {pat}'}
    if json_mode:
        headers['Content-Type'] = 'application/json'
    return headers


def base_url(path=''):
    base = os.environ['AIRTABLE_BASE_ID']
    return f'https://api.airtable.com/v0/{base}/{path}'


def schema(table=None):
    base = os.environ['AIRTABLE_BASE_ID']
    url = f'https://api.airtable.com/v0/meta/bases/{base}/tables'
    r = requests.get(url, headers=api_headers(json_mode=False), timeout=30)
    r.raise_for_status()
    data = r.json()
    if table:
        return next((t for t in data.get('tables', []) if t.get('name') == table), None)
    return data


def list_records(table, max_records=5, view=None, filter_formula=None, fields=None, offset=None):
    params = {'maxRecords': max_records}
    if view:
        params['view'] = view
    if filter_formula:
        params['filterByFormula'] = filter_formula
    if fields:
        params['fields[]'] = fields
    if offset:
        params['offset'] = offset
    r = requests.get(base_url(table), headers=api_headers(), params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def list_all_records(table, view=None, filter_formula=None, fields=None):
    records = []
    offset = None
    while True:
        data = list_records(table, max_records=100, view=view, filter_formula=filter_formula, fields=fields, offset=offset)
        records.extend(data.get('records', []))
        offset = data.get('offset')
        if not offset:
            break
    return {'records': records, 'count': len(records)}


def create_record(table, fields):
    r = requests.post(base_url(table), headers=api_headers(), json={'fields': fields}, timeout=30)
    if not r.ok:
        raise requests.HTTPError(r.text, response=r)
    return r.json()


def bulk_create(table, records):
    created = []
    for i in range(0, len(records), BATCH_LIMIT):
        chunk = records[i:i+BATCH_LIMIT]
        r = requests.post(base_url(table), headers=api_headers(), json={'records': [{'fields': x} for x in chunk]}, timeout=30)
        if not r.ok:
            raise requests.HTTPError(r.text, response=r)
        created.extend(r.json().get('records', []))
    return {'records': created, 'count': len(created)}


def update_record(table, record_id, fields):
    r = requests.patch(base_url(f'{table}/{record_id}'), headers=api_headers(), json={'fields': fields}, timeout=30)
    if not r.ok:
        raise requests.HTTPError(r.text, response=r)
    return r.json()


def upsert(table, fields, merge_on):
    value = fields.get(merge_on)
    if value is None:
        raise ValueError(f'merge_on field missing from payload: {merge_on}')
    formula = f"{{{merge_on}}}='{str(value).replace("'", "\\'")}'"
    existing = list_all_records(table, filter_formula=formula).get('records', [])
    if existing:
        return {'action': 'update', 'record': update_record(table, existing[0]['id'], fields)}
    return {'action': 'create', 'record': create_record(table, fields)}


def delete_record(table, record_id):
    r = requests.delete(base_url(f'{table}/{record_id}'), headers=api_headers(json_mode=False), timeout=30)
    if not r.ok:
        raise requests.HTTPError(r.text, response=r)
    return r.json()


def bulk_delete(table, record_ids=None, filter_formula=None, keep_filter=None):
    ids = record_ids or [r['id'] for r in list_all_records(table, filter_formula=filter_formula).get('records', [])]
    if keep_filter:
        keep = {r['id'] for r in list_all_records(table, filter_formula=keep_filter).get('records', [])}
        ids = [x for x in ids if x not in keep]
    deleted = []
    for i in range(0, len(ids), BATCH_LIMIT):
        chunk = ids[i:i+BATCH_LIMIT]
        params = [('records[]', rid) for rid in chunk]
        r = requests.delete(base_url(table), headers=api_headers(json_mode=False), params=params, timeout=30)
        if not r.ok:
            raise requests.HTTPError(r.text, response=r)
        deleted.extend(r.json().get('records', []))
    return {'records': deleted, 'count': len(deleted)}


def cleanup_table(table, keep_latest_n=0, keep_filter=None):
    records = list_all_records(table).get('records', [])
    if keep_latest_n > 0:
        records = sorted(records, key=lambda r: r.get('createdTime', ''), reverse=True)
        keep_ids = {r['id'] for r in records[:keep_latest_n]}
        target_ids = [r['id'] for r in records if r['id'] not in keep_ids]
    else:
        target_ids = [r['id'] for r in records]
    return bulk_delete(table, record_ids=target_ids, keep_filter=keep_filter)


def main():
    load_env()
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('schema')
    s.add_argument('--table', default=None)
    l = sub.add_parser('list')
    l.add_argument('table')
    l.add_argument('--max', type=int, default=5)
    l.add_argument('--view')
    l.add_argument('--filter-formula')
    la = sub.add_parser('list-all')
    la.add_argument('table')
    la.add_argument('--view')
    la.add_argument('--filter-formula')
    c = sub.add_parser('create')
    c.add_argument('table')
    c.add_argument('fields_json')
    bc = sub.add_parser('bulk-create')
    bc.add_argument('table')
    bc.add_argument('records_json')
    u = sub.add_parser('update')
    u.add_argument('table')
    u.add_argument('record_id')
    u.add_argument('fields_json')
    up = sub.add_parser('upsert')
    up.add_argument('table')
    up.add_argument('fields_json')
    up.add_argument('--merge-on', required=True)
    d = sub.add_parser('delete')
    d.add_argument('table')
    d.add_argument('record_id')
    bd = sub.add_parser('bulk-delete')
    bd.add_argument('table')
    bd.add_argument('--record-ids-json')
    bd.add_argument('--filter-formula')
    bd.add_argument('--keep-filter')
    cl = sub.add_parser('cleanup')
    cl.add_argument('table')
    cl.add_argument('--keep-latest', type=int, default=0)
    cl.add_argument('--keep-filter')
    args = ap.parse_args()
    if args.cmd == 'schema':
        print(json.dumps(schema(args.table), indent=2))
    elif args.cmd == 'list':
        print(json.dumps(list_records(args.table, args.max, args.view, args.filter_formula), indent=2))
    elif args.cmd == 'list-all':
        print(json.dumps(list_all_records(args.table, args.view, args.filter_formula), indent=2))
    elif args.cmd == 'create':
        print(json.dumps(create_record(args.table, json.loads(args.fields_json)), indent=2))
    elif args.cmd == 'bulk-create':
        print(json.dumps(bulk_create(args.table, json.loads(args.records_json)), indent=2))
    elif args.cmd == 'update':
        print(json.dumps(update_record(args.table, args.record_id, json.loads(args.fields_json)), indent=2))
    elif args.cmd == 'upsert':
        print(json.dumps(upsert(args.table, json.loads(args.fields_json), args.merge_on), indent=2))
    elif args.cmd == 'delete':
        print(json.dumps(delete_record(args.table, args.record_id), indent=2))
    elif args.cmd == 'bulk-delete':
        ids = json.loads(args.record_ids_json) if args.record_ids_json else None
        print(json.dumps(bulk_delete(args.table, ids, args.filter_formula, args.keep_filter), indent=2))
    elif args.cmd == 'cleanup':
        print(json.dumps(cleanup_table(args.table, args.keep_latest, args.keep_filter), indent=2))

if __name__ == '__main__':
    main()
