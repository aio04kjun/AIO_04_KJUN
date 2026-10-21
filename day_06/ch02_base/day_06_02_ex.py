from pydantic import BaseModel, ValidationError


class Book(BaseModel):
    title: str
    price: int
    in_stock: bool = True
    note: str | None = None

def main() -> None:
    book = Book(title='파이썬 기초', price='19000')
    print(book.model_dump())
   
    
    try:
        Book(price=19000)
    except ValidationError as e:
        print(e.errors()[0]['loc'], e.errors()[0]['type'])


if __name__ == '__main__':
    main()    


    
