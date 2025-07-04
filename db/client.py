import os
from dotenv import load_dotenv
from supabase import create_client, Client

# .env 파일 로드 (보안을 위해 환경변수 사용)
load_dotenv()

def _validate_environment():
    """환경변수 검증"""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url:
        raise ValueError("SUPABASE_URL 환경변수가 설정되지 않았습니다. .env 파일을 확인해주세요.")
    
    if not key:
        raise ValueError("SUPABASE_KEY 환경변수가 설정되지 않았습니다. .env 파일을 확인해주세요.")
    
    # URL 형식 검증
    if not url.startswith("https://") or ".supabase.co" not in url:
        raise ValueError("SUPABASE_URL이 올바른 Supabase URL 형식이 아닙니다.")
    
    # 키 형식 검증 (JWT 토큰 형식)
    if not key.startswith("eyJ"):
        raise ValueError("SUPABASE_KEY가 올바른 JWT 토큰 형식이 아닙니다.")
    
    return url, key

def init_supabase():
    """Supabase 클라이언트 초기화 및 반환"""
    url, key = _validate_environment()
    return create_client(url, key)

def get_supabase_client():
    """Supabase 클라이언트 반환 (기존 함수와 호환성 유지)"""
    url, key = _validate_environment()
    return create_client(url, key)

def get_media_outlet_id(supabase: Client, outlet_name: str):
    """언론사 이름으로 ID 조회"""
    try:
        response = supabase.table('media_outlets').select("id").eq('name', outlet_name).execute()
        if response.data:
            return response.data[0]['id']
        else:
            print(f"❌ 언론사 '{outlet_name}'을 찾을 수 없습니다.")
            return None
    except Exception as e:
        print(f"❌ 언론사 ID 조회 실패: {e}")
        return None

def get_category_id(supabase: Client, category_name: str):
    """카테고리 이름으로 ID 조회"""
    try:
        response = supabase.table('categories').select("id").eq('name', category_name).execute()
        if response.data:
            return response.data[0]['id']
        else:
            print(f"❌ 카테고리 '{category_name}'을 찾을 수 없습니다.")
            return None
    except Exception as e:
        print(f"❌ 카테고리 ID 조회 실패: {e}")
        return None 