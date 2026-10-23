from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(r'C:\AIO_04_kjun')
OUT = Path(__file__).resolve().parent
FONT = r'C:\Windows\Fonts\malgun.ttf'
MONO = r'C:\Windows\Fonts\consola.ttf'
items = [
    ('day_04', '실습 파일 준비', 'day_04/day_04_01.py', [(1,1)]),
    ('day_05', 'FastAPI 시작과 HTTP 메서드', 'day_05/05.FastAPI_uvicorn/labs/lesson02.py', [(1,14)]),
    ('day_06', 'Pydantic: 필수값과 기본값', 'day_06/ch02_base/day_06_02.py', [(1,15)]),
    ('day_07', '완료 순서와 요청 ID 연결 확인', 'day_07/03/main.py', [(36,45)]),
    ('day_08', '할인 경계값: 10000원도 할인 대상', 'day_08/lesson_04_ai_test_cases/main.py', [(1,21)]),
]
for day, title, source, ranges in items:
    lines = (ROOT/source).read_text(encoding='utf-8-sig').splitlines()
    excerpt = [(n,lines[n-1]) for a,b in ranges for n in range(a,min(b,len(lines))+1)]
    h = max(360, 225 + len(excerpt)*34)
    im = Image.new('RGB',(1500,h),'#101827')
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((22,22,1478,h-22),18,fill='#192438')
    d.text((52,42),f'{day}  |  {title}',font=ImageFont.truetype(FONT,30),fill='#f1f5fb')
    d.text((52,92),source,font=ImageFont.truetype(MONO,22),fill='#8fb8ef')
    for i,(n,line) in enumerate(excerpt):
        y=143+i*34
        d.text((48,y),f'{n:>3}',font=ImageFont.truetype(MONO,22),fill='#6b809e')
        d.text((112,y),line.expandtabs(4),font=ImageFont.truetype(FONT,23),fill='#d6e2f3')
    d.text((52,h-52),'실제 소스 발췌 · 가독성을 위해 이미지화 · 실행 화면 아님',font=ImageFont.truetype(FONT,18),fill='#8f9fb6')
    im.save(OUT/f'{day}.png')
    print(day, source, [(n, text) for n,text in excerpt])
