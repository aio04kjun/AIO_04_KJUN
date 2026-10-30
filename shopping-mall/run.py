"""Run from this folder: python run.py --demo, or python run.py for Supabase."""
import argparse
import os
from pathlib import Path

import uvicorn

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='ORBIT shopping mall')
    parser.add_argument('--demo', action='store_true', help='Local in-memory experience; no Supabase connection')
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--reload', action='store_true')
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('port must be 1..65535')
    env_file = Path(__file__).with_name('.env')
    if args.demo:
        os.environ['SHOP_DEMO'] = 'true'
        os.environ['APP_ORIGIN'] = f'http://localhost:{args.port}'
        print('LOCAL DEMO: data resets on restart. Login: demo@orbit.local / Orbit1234!')
    uvicorn.run('app.main:app', host='127.0.0.1', port=args.port,
        reload=args.reload, proxy_headers=False,
        env_file=str(env_file) if env_file.exists() and not args.demo else None)
