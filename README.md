# BlindSpot Backend

언론사별 뉴스 기사를 수집하고 분석하여 편향성을 분석하는 백엔드 시스템입니다.

## 🎯 이 프로젝트가 하는 일

1. **뉴스 수집**: 여러 언론사에서 자동으로 기사를 모아옵니다
2. **똑똑한 분석**: AI가 비슷한 주제의 기사들을 묶어주고 요약합니다  
3. **편향성 분석**: 언론사별로 어떤 시각 차이가 있는지 분석합니다
4. **결과 리포트**: 분석 결과를 보기 쉬운 보고서로 만들어줍니다

## 🚀 빠른 시작 (5분 설정)

### 1단계: 프로젝트 준비
```bash
# 이 프로젝트를 다운로드했다면, 폴더로 이동
cd blindspot_backend

# 필요한 패키지 설치
pip install -r requirements.txt
```

### 2단계: 환경 설정 (.env 파일 만들기)
프로젝트 폴더에 `.env` 파일을 만들고 아래 내용을 복사해서 넣으세요:

```bash
# Supabase 설정 (데이터베이스)
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-anon-key-here

# OpenAI 설정 (AI 분석용)
OPENAI_API_KEY=your-openai-api-key-here
```

**📝 API 키 받는 방법:**
- **Supabase**: [supabase.com](https://supabase.com) → 프로젝트 생성 → Settings → API
- **OpenAI**: [platform.openai.com](https://platform.openai.com) → API keys

### 3단계: 실행해보기
```bash
# 전체 파이프라인 실행 (크롤링 → 분석 → 리포트 생성)
python run_pipeline.py
```

**🎉 성공하면**: `reports/` 폴더에 분석 리포트가 생성됩니다!

## 📂 폴더 구조 (한눈에 보기)

```
blindspot_backend/
├── crawlers/           # 📰 뉴스 수집기들
│   ├── crawl_hani.py      # 한겨레
│   ├── crawl_chosun.py    # 조선일보  
│   ├── crawl_kbs.py       # KBS
│   └── crawl_ytn.py       # YTN
│
├── analyzer/           # 🧠 똑똑한 분석기들
│   ├── embed_articles.py     # 기사를 숫자로 변환
│   ├── cluster_articles.py   # 비슷한 기사끼리 묶기
│   └── summarize_clusters.py # 요약 및 분석
│
├── db/                 # 🗄️ 데이터베이스 연결
│   ├── client.py         # DB 연결
│   └── upload_articles.py # 데이터 저장
│
├── utils/              # 🛠️ 유틸리티 함수들
│   └── report_utils.py   # 리포트 생성 유틸
│
├── reports/            # 📊 결과 보고서들
├── run_pipeline.py     # 🔁 전체 실행하기
└── main_crawler.py     # 📰 뉴스만 수집하기
```

## 🛠️ 개별 기능 사용법

### 뉴스만 수집하고 싶다면
```bash
python main_crawler.py
```

### 데이터베이스 연결 테스트
```bash
python -m db.test
```

### 이미 수집된 데이터로 분석만 하려면
```bash
python run_cluster_save.py
```

## 📋 지원하는 언론사 & 카테고리

| 언론사 | 정치 | 경제 | 사회 |
|--------|------|------|------|
| 한겨레 | ✅ | ✅ | ✅ |
| 조선일보 | ✅ | ✅ | ✅ |
| KBS | ✅ | ✅ | ✅ |
| YTN | ✅ | ✅ | ✅ |

## 🔧 고급 설정 (선택사항)

### 추가 환경변수
```bash
# OpenAI 모델 설정 (기본값 사용해도 됨)
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_EMBEDDING_MODEL=text-embedding-ada-002
```

### 필요한 Python 패키지
```bash
pip install openai supabase playwright scikit-learn pandas numpy python-dotenv
```

## 📊 결과물 확인하기

### 분석 리포트 위치
```
reports/blindspot_analysis_YYYYMMDD_HHMMSS.md
```

### 리포트에서 볼 수 있는 것들
- 📈 클러스터별 주제 분석
- 📰 언론사별 기사 분포  
- 🎯 편향성 분석 결과
- 📝 주요 이슈 요약

## ❗ 자주 발생하는 문제 해결

### "환경변수가 설정되지 않았습니다" 에러
➡️ `.env` 파일이 프로젝트 루트 폴더에 있는지 확인하세요

### "Supabase 연결 실패" 에러  
➡️ SUPABASE_URL과 SUPABASE_KEY가 올바른지 확인하세요

### "OpenAI API 에러"
➡️ OPENAI_API_KEY가 유효하고, 크레딧이 있는지 확인하세요

### 크롤링 중 "Execution context was destroyed" 메시지
➡️ 정상적인 메시지입니다. 크롤링은 계속 진행됩니다

## 🔒 보안 주의사항

- ✅ `.env` 파일은 Git에 업로드되지 않습니다 (안전함)
- ❌ 코드에 직접 API 키를 적지 마세요
- 💡 API 키를 공유하거나 공개하지 마세요

## 🎯 다음 단계

1. **첫 실행**: `python run_pipeline.py`로 전체 파이프라인 실행해보기
2. **결과 확인**: `reports/` 폴더의 분석 리포트 읽어보기  
3. **개선하기**: 원하는 언론사나 분석 기능 추가하기

## 🆘 도움이 필요하면

- 각 파일의 코드에 주석이 있으니 참고하세요
- 에러 메시지를 잘 읽어보면 해결 방법이 나와있어요
- 테스트 파일(`db/test.py`)로 연결 상태를 확인할 수 있어요

---

**🎉 축하합니다!** 이제 BlindSpot Backend를 사용할 준비가 되었습니다. 