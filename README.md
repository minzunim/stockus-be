# 미국 주식 커뮤니티 요약

## 프로젝트 실행 방법

```
poetry install
poetry shell
poetry run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Updates
- 2025-07-06 
    - 3-layered-architecture로 리팩토링
    - yfinance API (미국 3대 시장 지수) 호출 500 에러 해결
        - curl_cffi로 session 객체 생성 방식 변경
        - yfinance 버전 업데이트

- 2025-07-07
    - 미국 3대 시장 지수 API 속도 개선
        - 비동기 방식으로 API 호출로 변경 (asyncio 도입)