"""Render an explanatory purchase flow as matching PNG and SVG images."""
from pathlib import Path
from html import escape
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent
W, H = 2000, 2470
image = Image.new('RGB', (W, H), '#f1f5f9')
draw = ImageDraw.Draw(image)
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">', '<title>상품 구매 시뮬레이션 — 테이블 데이터의 변화</title>', '<desc>김하늘 회원이 머그컵 두 개와 노트 한 개를 29000원에 구매하는 여섯 단계입니다.</desc>']
FONT = 'C:/Windows/Fonts/malgun.ttf'
BOLD = 'C:/Windows/Fonts/malgunbd.ttf'

def box(x,y,w,h,fill,stroke='none',radius=12):
    draw.rounded_rectangle((x,y,x+w,y+h),radius,fill,None if stroke=='none' else stroke,2)
    svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')

def txt(x,y,value,size=25,color='#1e293b',bold=False,max_width=None):
    font=ImageFont.truetype(BOLD if bold else FONT,size)
    if max_width:
        assert draw.textbbox((0,0),value,font=font)[2] <= max_width, value
    draw.text((x,y),value,fill=color,font=font)
    svg.append(f'<text x="{x}" y="{y+size}" font-family="Malgun Gothic, sans-serif" font-size="{size}" fill="{color}" font-weight="{700 if bold else 400}">{escape(value)}</text>')

def table(x,y,widths,headers,rows):
    width=sum(widths)
    box(x,y,width,44,'#e5edf5',radius=0)
    for ri,row in enumerate([headers]+rows):
        yy=y+ri*44
        if ri: box(x,yy,width,44,'#f6f9fc' if ri%2==0 else '#ffffff',radius=0)
        xx=x
        for i,v in enumerate(row):
            txt(xx+12,yy+8,str(v),21,'#102c46' if ri==0 else '#334155',ri==0,widths[i]-24)
            xx+=widths[i]

def step(y,h,num,title,lines,badge):
    box(65,y+5,1870,h,'#dde6ef',radius=18)
    box(60,y,1870,h,'#ffffff','#cbd5e1',18)
    box(84,y+23,68,56,'#102c46',radius=12)
    txt(97,y+30,num,29,'#ffffff',True)
    txt(172,y+27,title,31,'#102c46',True,max_width=430)
    for i,s in enumerate(lines): txt(94,y+105+i*40,s,25,'#526579',max_width=505)
    box(94,y+h-58,490,36,'#e6f4fa',radius=8)
    txt(106,y+h-55,badge,20,'#036b91',True,max_width=466)

def heading(y,value): txt(640,y,value,25,'#036b91',True,max_width=1250)

def arrow(y):
    pts=[(980,y),(1000,y+16),(1020,y)]
    draw.line(pts,fill='#7c95aa',width=4)
    svg.append(f'<polyline points="980,{y} 1000,{y+16} 1020,{y}" fill="none" stroke="#7c95aa" stroke-width="4"/>')

box(0,0,W,H,'#f1f5f9',radius=0)
txt(65,35,'상품 구매 시뮬레이션',48,'#102c46',True)
txt(67,104,'김하늘(U1) 회원이 머그컵 2개와 노트 1개를 구매합니다.',28,'#526579')
box(65,158,1870,52,'#102c46')
txt(87,168,'12,000원 × 2개  +  5,000원 × 1개  =  총 29,000원',27,'#ffffff',True)

step(240,250,'01','상품 조회 · 로그인',[
    '상품 목록과 가격을 확인합니다.',
    '비회원은 로그인 후 원래 화면으로 복귀.'
], '조회: products  |  기존 회원 U1 기준')
heading(263,'products — 조회만 수행, 재고 변경 없음')
table(640,307,[160,410,310,360],['id','name / 상품명','price / 가격','stock / 재고'],[
    ['P1','우주 머그컵','12,000원','10개'],['P2','달 노트','5,000원','20개']])
txt(652,451,'users: U1 = 김하늘  ·  로그인은 인증 세션 처리이며 회원 행을 추가하지 않습니다.',22,'#526579')
arrow(496)

step(520,260,'02','장바구니 담기',[
    '선택한 상품과 수량을 저장합니다.',
    '같은 상품을 또 담으면 수량만 증가.'
], '추가: cart_items 2행  |  재고 유지')
heading(543,'cart_items — INSERT (추가)')
table(640,587,[160,320,400,360],['id','user_id / 회원','product_id / 상품','quantity / 수량'],[
    ['C1','U1','P1 · 우주 머그컵','2'],['C2','U1','P2 · 달 노트','1']])
txt(652,732,'가격은 products에서 조회합니다. 아직 주문·결제 레코드는 없습니다.',23,'#526579')
arrow(786)

step(810,400,'03','주문 생성',[
    '서버가 현재 가격·재고를 확인합니다.',
    '주문 1행 + 주문 항목 2행을 저장.',
    '상품명·단가는 이 시점 값으로 보존.',
    '배송정보도 주문에 함께 저장합니다.'
], '추가: orders + order_items  |  재고 유지')
heading(833,'orders — INSERT (추가)')
table(640,875,[160,280,400,400],['id','user_id','status / 상태','total_amount / 총액'],[
    ['O1','U1','pending · 결제 대기','29,000원']])
heading(985,'order_items — INSERT (추가): 두 행 모두 order_id = O1')
table(640,1027,[110,150,170,330,280,200],['id','order_id','product_id','product_name','unit_price','quantity'],[
    ['I1','O1','P1','우주 머그컵','12,000원','2'],
    ['I2','O1','P2','달 노트','5,000원','1']])
txt(652,1170,'항목 금액: 24,000원 + 5,000원 = 29,000원  ·  주문과 항목은 함께 저장합니다.',22,'#526579')
arrow(1216)

step(1240,400,'04','모의 결제 성공',[
    '첫 시도에 결제 M1을 생성합니다.',
    '최종 재고를 확인하고 결제를 확정.',
    '재고·결제·주문을 한 번에 변경합니다.',
    '중복 요청은 재고를 다시 줄이지 않음.'
], '추가: payments  |  변경: 결제·주문·재고')
heading(1263,'payments: M1 / order_id = O1 / amount = 29,000원')
table(640,1305,[560,300,380],['테이블 · 컬럼','변경 전','변경 후'],[
    ['products · P1.stock','10개','8개'],
    ['products · P2.stock','20개','19개'],
    ['payments · M1.status','pending','succeeded · 성공'],
    ['orders · O1.status','pending','paid · 결제 완료']])
txt(652,1544,'M1.paid_at에 성공 시각 저장  ·  확정 변경은 하나의 DB 트랜잭션으로 처리',22,'#526579')
txt(652,1585,'실패 시: payments = failed / orders = pending / 재고는 그대로 유지',22,'#9a4f17',True)
arrow(1646)

step(1670,210,'05','상품 목록으로 이동',[
    '결제 완료 안내 후 목록으로 돌아갑니다.'
], '조회: products  |  장바구니는 유지')
heading(1693,'상품 목록에 반영되는 최신 재고')
table(640,1735,[550,320,370],['상품','결제 전 재고','결제 후 재고'],[
    ['P1 · 우주 머그컵','10개','8개'],['P2 · 달 노트','20개','19개']])
arrow(1886)

step(1910,290,'06','구매 내역 확인',[
    '내 주문 O1과 상품·결제를 조회합니다.',
    '나중에 상품 가격이 올라도',
    '과거 구매 금액은 그대로 유지됩니다.'
], '조회: orders + order_items + payments')
heading(1933,'연결 키: U1 → O1 → 주문 항목 I1·I2 + 결제 M1')
table(640,1975,[560,680],['조회 테이블','사용자에게 표시할 내용'],[
    ['orders · O1','paid / 총 29,000원 / 배송정보'],
    ['order_items · I1, I2','머그컵 2개 + 노트 1개 / 구매 당시 단가'],
    ['payments · M1','succeeded / 29,000원 / 성공 시각']])
txt(652,2160,'P1 현재가가 15,000원으로 바뀌어도 I1 구매 단가는 12,000원입니다.',23,'#036b91',True)

box(65,2240,1870,170,'#e0ebf3',radius=16)
txt(90,2256,'읽는 순서: 위 → 아래   |   INSERT = 행 추가   ·   UPDATE = 기존 값 변경',25,'#102c46',True)
txt(90,2302,'U1·P1·O1 등은 설명용 별칭이며 실제 ID는 UUID입니다. 배송비 0원 · 모의 결제 기준입니다.',24,'#334e68')
txt(90,2347,'바로 구매는 02번을 건너뛰고 03번으로 진행합니다. 결제 후 장바구니 항목은 직접 삭제합니다.',24,'#334e68')

svg.append('</svg>')
image.save(OUT/'purchase-simulation.png')
(OUT/'purchase-simulation.svg').write_text('\n'.join(svg),encoding='utf-8')
print('Generated purchase-simulation.png and purchase-simulation.svg')
