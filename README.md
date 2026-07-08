# HWPX GenAI Template Agent

HWPX 공문서 양식을 검색하고, 사용자 요청을 필드 데이터로 변환한 뒤, 템플릿 파일에 값을 채워 새 HWPX 문서를 생성하는 실험용 에이전트입니다.

## 주요 기능

- HWPX 누름틀 필드명 추출
- 템플릿 설명과 필드 스키마를 Qdrant에 인덱싱
- 자연어 요청에 맞는 템플릿 검색
- LLM 응답을 JSON 필드 데이터로 변환
- 템플릿 HWPX 파일에 필드 값 주입

## 구조

```text
core/
├── hwpx_processor.py
├── llm_agent.py
└── vector_store.py
config.py
main.py
models.py
test/
└── hwpx_complete_poc.py
```

## 준비

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## 실행

```bash
python main.py
```

`templates/`에 HWPX 템플릿을 넣으면 실행 시 자동으로 인덱싱합니다.

## 검증

```bash
python -m py_compile main.py core/hwpx_processor.py core/vector_store.py core/llm_agent.py models.py
```

## 데이터 정책

실제 HWPX 템플릿, 생성 결과, Qdrant 로컬 DB, `.env`는 Git에 포함하지 않습니다.
