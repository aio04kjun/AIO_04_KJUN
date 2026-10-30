"""Generate matching PNG/SVG table diagrams using Pillow (no web runtime)."""
from pathlib import Path
from html import escape
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent
W, H = 2200, 1780
im = Image.new('RGB', (W, H), '#f1f5f9')
d = ImageDraw.Draw(im)
parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">', '<title>쇼핑몰 최소 ERD — 6개 테이블</title>', '<desc>회원과 상품을 중심으로 장바구니, 주문, 주문 항목, 결제의 관계를 표시합니다. 화살표는 부모에서 자식 외래키로 향합니다.</desc>']
FONT = 'C:/Windows/Fonts/malgun.ttf'
BOLD = 'C:/Windows/Fonts/malgunbd.ttf'

def rect(x, y, w, h, fill, outline=None, radius=0):
    d.rounded_rectangle((x,y,x+w,y+h), radius, fill, outline, 2)
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{outline or "none"}" stroke-width="2"/>')

def text(x,y,s,size=23,color='#1e293b',bold=False):
    font=ImageFont.truetype(BOLD if bold else FONT,size)
    d.text((x,y),s,font=font,fill=color)
    parts.append(f'<text x="{x}" y="{y+size}" font-family="Malgun Gothic, sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{color}">{escape(s)}</text>')

def line(points,color='#64748b',width=4,arrow=False):
    d.line(points,fill=color,width=width,joint='curve')
    parts.append(f'<polyline points="{" ".join(f"{x},{y}" for x,y in points)}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round"/>')
    if arrow:
        x,y=points[-1]; px,py=points[-2]
        if x!=px:
            sign=1 if x>px else -1
            tri=[(x,y),(x-sign*14,y-8),(x-sign*14,y+8)]
        else:
            sign=1 if y>py else -1
            tri=[(x,y),(x-8,y-sign*14),(x+8,y-sign*14)]
        d.polygon(tri,fill=color)
        parts.append(f'<polygon points="{" ".join(f"{a},{b}" for a,b in tri)}" fill="{color}"/>')

def label(x,y,s,width):
    rect(x,y,width,42,'#f1f5f9',radius=9)
    text(x+10,y+5,s,22,bold=True)

def card(x,y,title,subtitle,rows):
    height=150+44*len(rows)
    rect(x+4,y+7,620,height,'#dce5ee',radius=18)
    rect(x,y,620,height,'#ffffff','#cbd5e1',18)
    rect(x,y,620,90,'#102c46',radius=16)
    rect(x,y+70,620,20,'#102c46')
    text(x+22,y+12,title,29,'#ffffff',True)
    text(x+22,y+53,subtitle,19,'#9edfff')
    rect(x+1,y+91,618,41,'#e6eef5')
    text(x+20,y+98,'키',19,bold=True)
    text(x+103,y+98,'컬럼 / 한글 의미',19,bold=True)
    text(x+466,y+98,'타입',19,bold=True)
    for i,(key,name,meaning,typ) in enumerate(rows):
        yy=y+136+44*i
        if i%2==1: rect(x+2,yy-3,616,44,'#f6f9fc')
        text(x+18,yy,key,19,'#036b91' if key else '#64748b',True)
        text(x+103,yy,name,18 if len(name)>13 else 21,bold=bool(key))
        text(x+285,yy+2,meaning,18,'#526579')
        text(x+466,yy+2,typ,19,'#526579')
    return height

rect(0,0,W,H,'#f1f5f9')
text(70,42,'쇼핑몰 최소 ERD',48,'#102c46',True)
text(72,113,'6개 테이블로 이해하는 상품 구매 흐름',27,'#526579')
text(72,165,'화살표: 부모 테이블 → FK를 가진 자식 테이블    |    1:N = 하나에 여러 개 연결',22,'#526579')

# Relationship paths are placed behind cards, with labels in the surrounding space.
line([(690,395),(790,395)],arrow=True)
line([(1510,440),(1410,440)],arrow=True)
line([(380,556),(380,940)],arrow=True)
line([(1820,688),(1820,845),(1100,845),(1100,940)],arrow=True)
line([(690,1110),(790,1110)],arrow=True)
line([(380,1442),(380,1565),(1820,1565),(1820,1310)],arrow=True)

card(70,230,'회원  USERS','Supabase 인증 계정과 1:1 연결',[
 ('PK/FK','id','회원 ID','uuid'),('','name','이름','varchar'),('','phone','연락처 *','varchar'),('','created_at','가입 시각','timestamptz')])
card(790,230,'장바구니  CART_ITEMS','회원 + 상품 조합은 중복 불가',[
 ('PK','id','항목 ID','uuid'),('FK','user_id','회원 ID','uuid'),('FK','product_id','상품 ID','uuid'),('','quantity','수량','integer')])
card(1510,230,'상품  PRODUCTS','현재 판매 정보와 재고',[
 ('PK','id','상품 ID','uuid'),('','name','상품명','varchar'),('','description','설명','text'),('','price','현재 가격','bigint'),('','stock','재고','integer'),('','image_url','이미지 *','text'),('','is_active','판매 여부','boolean')])
card(70,940,'주문  ORDERS','회원 1명 → 여러 주문',[
 ('PK','id','주문 ID','uuid'),('FK','user_id','회원 ID *','uuid'),('','status','주문 상태','varchar'),('','total_amount','총액','bigint'),('','recipient_name','수령인','varchar'),('','recipient_phone','연락처','varchar'),('','shipping_address','배송 주소','text'),('','created_at','주문 시각','timestamptz')])
card(790,940,'주문 항목  ORDER_ITEMS','주문 당시 상품명·단가 보존',[
 ('PK','id','항목 ID','uuid'),('FK','order_id','주문 ID','uuid'),('FK','product_id','상품 ID','uuid'),('','product_name','구매 상품명','varchar'),('','unit_price','구매 단가','bigint'),('','quantity','구매 수량','integer')])
card(1510,940,'결제  PAYMENTS','주문별 결제 최대 1행 · 모의 결제',[
 ('PK','id','결제 ID','uuid'),('FK/UK','order_id','주문 ID','uuid'),('','amount','결제금액','bigint'),('','status','결제 상태','varchar'),('','paid_at','성공 시각 *','timestamptz')])

label(696,345,'1:N',85)
label(1414,389,'1:N',85)
label(196,695,'1:N  주문',170)
label(976,793,'1:N  원본 상품 참조',300)
label(696,1060,'1:N',85)
label(892,1539,'1:0..1  주문별 결제',310)

rect(70,1630,2060,108,'#e0ebf3',radius=16)
text(94,1644,'PK 기본키   ·   FK 외래키   ·   UK 중복 불가   ·   * NULL 허용   ·   금액 단위: 원',23,'#102c46',True)
text(94,1687,'구매 흐름: 상품 조회 → 장바구니 → 주문 + 주문 항목 → 결제 성공 → 재고 차감·주문 완료',24,'#334e68')
parts.append('</svg>')
im.save(OUT/'erd-tables.png')
(OUT/'erd-tables.svg').write_text('\n'.join(parts),encoding='utf-8')
print('Generated erd-tables.png and erd-tables.svg')
