# BlindSpot Backend

언론사별 뉴스 기사를 수집하고 분석하여 편향성을 분석하는 백엔드 시스템입니다.

## 📂 디렉토리 구조

```
blindspot_backend/
├── crawlers/                      # 📰 언론사별 기사 수집
│   ├── crawl_hani.py             # 한겨레 크롤러
│   ├── crawl_chosun.py           # 조선일보 크롤러
│   ├── crawl_kbs.py              # KBS뉴스 크롤러
│   ├── crawl_ytn.py              # YTN 크롤러
│   └── ytn_debug.py              # YTN 디버그용
│
├── analyzer/                      # 🧠 기사 분석
│   ├── embed_articles.py         # 임베딩 처리
│   ├── cluster_articles.py       # 클러스터링 처리
│   ├── summarize_clusters.py     # GPT 요약 처리
│   └── __init__.py               # 패키지 초기화
│
├── supabase/                      # 🛠️ Supabase 연동
│   ├── client.py                 # supabase 클라이언트
│   ├── upload_articles.py        # 기사 업로드 함수
│   ├── test.py                   # 연결 테스트
│   └── __init__.py               # 패키지 초기화
│
├── reports/                       # 📋 분석 리포트 저장
│   └── blindspot_analysis_*.md   # 생성된 분석 리포트들
│
├── run_pipeline.py                # 🔁 전체 파이프라인 실행
├── main_crawler.py               # 크롤링 실행 (병렬 처리)

├── .gitignore                    # Git 무시 파일
└── README.md                     # 이 파일
```

## 🚀 사용법

### 1. 전체 파이프라인 실행

```bash
python run_pipeline.py
```

이 명령어는 다음 순서로 실행됩니다:
1. 📰 기사 크롤링 (병렬 처리)
2. 🧠 기사 분석 (임베딩 → 클러스터링 → 요약)
3. 📊 결과 리포트 생성

### 2. 개별 크롤링만 실행

```bash
python main_crawler.py
```

### 3. Supabase 연결 테스트

```bash
python -m supabase.test
```

## 🔧 설정

### 필요한 환경 변수

프로젝트 루트에 `.env` 파일을 생성하고 다음 환경변수를 설정하세요:

```bash
# Supabase 연결 정보
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-or-service-role-key

# OpenAI API 키 (분석용)
OPENAI_API_KEY=your-openai-api-key

# OpenAI 모델명
OPENAI_MODEL=gpt-3.5-turbo

# OpenAI 임베딩 모델명
OPENAI_EMBEDDING_MODEL=text-embedding-ada-002
```

### 보안 주의사항 ⚠️

1. **절대 하드코딩 금지**: URL, API 키 등을 코드에 직접 입력하지 마세요
2. **환경변수 사용**: 모든 민감한 정보는 `.env` 파일에 저장하세요
3. **Git 무시**: `.env` 파일은 `.gitignore`에 포함되어 있어 Git에 커밋되지 않습니다
4. **키 관리**: 
   - Supabase anon 키: 클라이언트용 (읽기/쓰기 제한)
   - Supabase service_role 키: 서버용 (전체 권한)
   - OpenAI API 키: 분석용 (사용량 모니터링 필요)

### 필요한 패키지

```bash
pip install openai supabase playwright scikit-learn pandas numpy
```

## 📊 기능

### 크롤링 (crawlers/)
- **한겨레**: 정치, 경제, 사회 카테고리
- **조선일보**: 정치, 경제, 사회 카테고리  
- **KBS뉴스**: 정치, 경제, 사회 카테고리
- **YTN**: 정치, 경제, 사회 카테고리

### 분석 (analyzer/)
- **임베딩**: OpenAI Embeddings API로 텍스트 벡터화
- **클러스터링**: K-means로 주제별 그룹화
- **요약**: GPT-4로 클러스터별 주제 분석
- **편향 분석**: 언론사별 편향성 통계

### 데이터베이스 (supabase/)
- **기사 저장**: 중복 체크 및 자동 저장
- **데이터 로드**: 분석용 기사 데이터 조회
- **언론사/카테고리 관리**: ID 매핑

## 📈 출력

### 분석 리포트
- 클러스터별 주제 분석
- 언론사별 기사 분포
- 편향성 통계 및 판정
- 마크다운 형식으로 저장

### 파일명 형식
```
reports/blindspot_analysis_YYYYMMDD_HHMMSS.md
```

## 🔄 파이프라인 흐름

```
1. 크롤링 → 2. DB 저장 → 3. 데이터 로드 → 4. 임베딩 → 5. 클러스터링 → 6. 요약 → 7. 리포트 생성
```

## ⚠️ 주의사항

- 크롤링 시 "Execution context was destroyed" 에러가 발생할 수 있지만, 실제 크롤링은 정상 작동합니다.
- OpenAI API 사용량에 주의하세요.
- Supabase 연결 정보는 보안에 유의하여 관리하세요.

## 🛠️ 개발

### 모듈 추가
- 새로운 크롤러: `crawlers/crawl_[언론사명].py`
- 새로운 분석 기능: `analyzer/` 디렉토리에 추가
- 새로운 DB 기능: `supabase/` 디렉토리에 추가
- 리포트 관리: `reports/` 디렉토리에 자동 저장 