"""Install/inspect the shop using an existing PostgreSQL config; never print secrets."""
import argparse
import json
import re
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
TABLES = ['users', 'products', 'cart_items', 'orders', 'order_items', 'payments']
FUNCTIONS = ['create_order', 'pay_mock_order', 'cancel_order', 'add_cart_item']


def connection_values(path):
    config = json.loads(path.read_text(encoding='utf-8-sig'))
    override = path.with_name('config.local.json')
    if override.exists() and override != path:
        config.update(json.loads(override.read_text(encoding='utf-8-sig')))
    result = {key: config[key] for key in ('host', 'port', 'dbname', 'user', 'password')}
    if not str(result['host']).endswith(('.supabase.com', '.supabase.co')):
        raise ValueError('The selected config must point to Supabase')
    return result


def without_transaction(source):
    return re.sub(r'^\s*(?:BEGIN|COMMIT|ROLLBACK);\s*$', '', source, flags=re.M)


def inspect(cur):
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name=ANY(%s)", (TABLES,))
    tables = sorted(row[0] for row in cur.fetchall())
    cur.execute("SELECT p.proname FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.proname=ANY(%s)", (FUNCTIONS,))
    functions = sorted(row[0] for row in cur.fetchall())
    print('Shop tables: ' + (', '.join(tables) or '(none)'))
    print('Shop functions: ' + (', '.join(functions) or '(none)'))
    return tables, functions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=PROJECT.parent / 'day_11/config.json')
    parser.add_argument('--apply', action='store_true', help='Install the new shop schema if no shop table exists')
    parser.add_argument('--verify', action='store_true', help='Run test data in a transaction that is always rolled back')
    args = parser.parse_args()
    import psycopg
    settings = connection_values(args.config.resolve())
    try:
        with psycopg.connect(**settings, autocommit=True, connect_timeout=10, sslmode='require',
                            options='-c statement_timeout=30000') as conn:
            with conn.cursor() as cur:
                tables, functions = inspect(cur)
                if args.apply:
                    with conn.transaction():
                        cur.execute("SELECT pg_advisory_xact_lock(hashtextextended('orbit-schema-install',0))")
                        tables, functions = inspect(cur)
                        if tables:
                            if set(tables) != set(TABLES) or set(functions) != set(FUNCTIONS):
                                raise RuntimeError('Existing shop objects differ; a reviewed migration is required')
                            print('Existing complete schema preserved; no DDL or seed executed.')
                        else:
                            for name in ('schema.sql', 'seed.sql', 'backend-functions.sql'):
                                source = (PROJECT / 'sql' / name).read_text(encoding='utf-8-sig')
                                cur.execute(without_transaction(source), prepare=False)
                                print('Installed: ' + name)
                    inspect(cur)
                if args.verify:
                    with conn.transaction(force_rollback=True):
                        # Temporary auth fixtures never commit and send no authentication emails.
                        for index in range(2):
                            cur.execute("INSERT INTO auth.users(id,email,raw_user_meta_data) VALUES(gen_random_uuid(),%s,%s::jsonb)",
                                (f'orbit-rollback-{index}@example.invalid', json.dumps({'name': '롤백 검증 회원'})))
                        source = (PROJECT / 'sql/verify.sql').read_text(encoding='utf-8-sig')
                        cur.execute(without_transaction(source), prepare=False)
                        while True:
                            if cur.description:
                                for row in cur.fetchall():
                                    if row and isinstance(row[0], str) and row[0].startswith('PASS:'):
                                        print(row[0])
                            if not cur.nextset():
                                break
                    print('Verification fixtures and all test writes rolled back.')
                print('Supabase database connection OK. API/Auth keys are configured separately in shopping-mall/.env.')
    except Exception as exc:
        print('Database operation failed: ' + type(exc).__name__ + '; SQLSTATE=' + str(getattr(exc, 'sqlstate', None)))
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
