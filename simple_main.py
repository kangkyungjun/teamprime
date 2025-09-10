"""간단한 서버 테스트"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI(title="Test Server")

@app.get("/")
async def root():
    return HTMLResponse("""
    <html>
        <head><title>테스트 서버</title></head>
        <body>
            <h1>서버가 정상 작동 중입니다!</h1>
            <p><a href="/login">로그인 페이지로 이동</a></p>
        </body>
    </html>
    """)

@app.get("/login")
async def login():
    return HTMLResponse("""
    <html>
        <head><title>로그인</title></head>
        <body>
            <h1>로그인 페이지</h1>
            <p>사용자명: teamprime</p>
            <p>비밀번호: teamprime123!</p>
        </body>
    </html>
    """)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)