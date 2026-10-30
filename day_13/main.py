# supabase Auth 연결 이메일 회원가입 API
# 두개 계정으로 가입 -로그인> 메모접근> 갱신> 로그아웃

import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, EmailStr,Field, SecretStr
from supabase.client import ClientOptions


load_dotenv(override=True)
print(os.getenv("host", ""))