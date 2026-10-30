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

supabase_url = os.getenv("supabase_url").strip().rsplit("/")
supabase_key = os.getenv("supabase_publishable_key").strip()
if not supabase_url or not supabase_key:
    raise RuntimeError("supabase_url or supabase_publishable_key missing")

app = FastAPI(title="Supabase Auth - 회원가입")

class SignupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email : EmailStr
    password : SecretStr = Field(min_length=8, max_length=128)

class SignupRequest(BaseModel):
    messege : str