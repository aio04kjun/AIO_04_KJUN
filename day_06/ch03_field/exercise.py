from pydantic import BaseModel, Field, ValidationError

class Product(BaseModel):
    title: str = Field(min_length=2, max_length=60)
    price: int = Field(gt=0)
    # TODO stock: 0보다 크거나 같아야 함, 기본값 = 0
    stock: int = Field(ge=0, default=0)
    # TODO sku: SKU-와 숫자 네자리 패턴
    sku: str = Field(pattern=r'^SKU-[0-9]{4}$')
    

def main() -> None:
    product1 = Product(title="노트북", price=1000000, sku="SKU-1234")
    print('검증성공', product1.model_dump())
    print('오류확인')

    try:
     product2 = Product(title="모니터", price=500000, sku="SKU-78")
    except ValidationError as e:
     print(e.errors()[0]['loc'], e.errors()[0]['type'])

        
if __name__ == '__main__':
    main()
