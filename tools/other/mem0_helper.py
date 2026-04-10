#!/usr/bin/env python3
import os, json, argparse
from pathlib import Path
from mem0 import MemoryClient

ENV_PATH = Path('/home/lazywork/.openclaw/workspace/.env.local')

def load_env():
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line=line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k,v=line.split('=',1)
            os.environ.setdefault(k,v)

def client():
    load_env()
    return MemoryClient(api_key=os.environ['MEM0_API_KEY'])

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    a = sub.add_parser('add')
    a.add_argument('--user-id', required=True)
    a.add_argument('--message', required=True)
    a.add_argument('--assistant', default='')
    s = sub.add_parser('search')
    s.add_argument('--user-id', required=True)
    s.add_argument('--query', required=True)
    args = ap.parse_args()
    c = client()
    if args.cmd == 'add':
        messages = [{"role":"user","content":args.message}]
        if args.assistant:
            messages.append({"role":"assistant","content":args.assistant})
        print(json.dumps(c.add(messages, user_id=args.user_id), indent=2, default=str))
    elif args.cmd == 'search':
        filters = {"OR": [{"user_id": args.user_id}]}
        print(json.dumps(c.search(args.query, version='v2', filters=filters), indent=2, default=str))

if __name__ == '__main__':
    main()
