"""Static PostgreSQL parser and ERD consistency checks; not a database integration test."""
import re
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT.parent / '.supabase-deps'))
import pglast
from pglast import ast


def main():
    for path in sorted((PROJECT / 'sql').glob('*.sql')):
        source = path.read_text(encoding='utf-8-sig')
        statements = pglast.parse_sql(source)
        blocks = pglast.parse_plpgsql(source)
        print(f'PASS {path.name}: {len(statements)} SQL statements; {len(blocks)} PL/pgSQL blocks')

    schema = (PROJECT / 'sql/schema.sql').read_text(encoding='utf-8-sig')
    types = {'int8': 'bigint', 'int4': 'integer', 'bool': 'boolean'}
    actual = {}
    for raw in pglast.parse_sql(schema):
        statement = raw.stmt
        if isinstance(statement, ast.CreateStmt):
            actual[statement.relation.relname] = {
                col.colname: types.get(col.typeName.names[-1].sval, col.typeName.names[-1].sval)
                for col in statement.tableElts if isinstance(col, ast.ColumnDef)
            }
    erd = (PROJECT / 'docs/erd.mmd').read_text(encoding='utf-8')
    expected = {}
    for table, body in re.findall(r'\b([A-Z_]+)\s*\{([^}]+)\}', erd):
        expected[table.lower()] = {
            name: kind for kind, name in re.findall(r'^\s*(\w+)\s+(\w+)', body, re.M)
        }
    assert actual == expected, f'ERD mismatch: SQL={actual}, ERD={expected}'
    assert schema.count('ENABLE ROW LEVEL SECURITY') == len(expected)
    print('PASS exact ERD column/type match; RLS enabled for all six tables')

    for path in (PROJECT / 'docs').glob('*.md'):
        for target in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8-sig')):
            if not target.startswith(('https://', 'http://', '#')):
                assert (path.parent / target).exists(), f'Broken link: {path} -> {target}'
    print('PASS local Markdown document links')


if __name__ == '__main__':
    main()
