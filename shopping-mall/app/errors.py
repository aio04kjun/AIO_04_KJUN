class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status = status
        self.code = code
        self.message = message


def not_found(name='대상'):
    return ApiError(404, 'NOT_FOUND', f'{name}을 찾을 수 없습니다.')
