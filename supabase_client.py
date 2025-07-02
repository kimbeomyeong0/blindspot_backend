from supabase import create_client, Client

# Supabase 연결 정보
SUPABASE_URL = "https://grcvxnnkfpewzejifesu.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdyY3Z4bm5rZnBld3plamlmZXN1Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MTQ3MTQ2MSwiZXhwIjoyMDY3MDQ3NDYxfQ.PHWwtDU5xr-QkM_R3oGWu-Cmyseiv253SwJw8rcN7ug"

def init_supabase():
    """Supabase 클라이언트 초기화 및 반환"""
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def get_supabase_client():
    """Supabase 클라이언트 반환 (기존 함수와 호환성 유지)"""
    return create_client(SUPABASE_URL, SUPABASE_KEY)

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

def save_article_to_db(supabase: Client, article_data=None, **kwargs):
    """기사를 Supabase에 저장 (모든 방식 지원)"""
    try:
        # 방식 1: save_article_to_db(supabase, article_data)
        if article_data is not None and isinstance(article_data, dict):
            title = article_data.get('title')
            content = article_data.get('content')
            url = article_data.get('url')
            media_outlet = article_data.get('media_outlet')
            category = article_data.get('category')
        # 방식 2: save_article_to_db(supabase, title=title, content=content, ...)
        else:
            title = kwargs.get('title')
            content = kwargs.get('content')
            url = kwargs.get('url')
            media_outlet = kwargs.get('media_outlet')
            category = kwargs.get('category')
        
        # 필수 데이터 확인
        if not all([title, content, url, media_outlet, category]):
            print(f"❌ 필수 데이터 누락: title={bool(title)}, content={bool(content)}, url={bool(url)}, media_outlet={bool(media_outlet)}, category={bool(category)}")
            return False
        
        # 중복 URL 체크
        existing = supabase.table('articles').select("id").eq('url', url).execute()
        if existing.data:
            print(f"⚠️ 이미 존재하는 URL (건너뜀): {title[:30]}...")
            return False
        
        # 언론사 ID 조회
        media_outlet_id = get_media_outlet_id(supabase, media_outlet)
        if not media_outlet_id:
            return False
        
        # 카테고리 ID 조회
        category_id = get_category_id(supabase, category)
        if not category_id:
            return False
        
        # DB에 저장할 데이터 준비
        db_data = {
            "title": title,
            "content": content, 
            "url": url,
            "media_outlet_id": media_outlet_id,
            "category_id": category_id,
            "published_at": "NOW()"  # 현재 시간으로 설정
        }
        
        # Supabase에 저장
        response = supabase.table('articles').insert(db_data).execute()
        
        if response.data:
            print(f"✅ DB 저장 성공: {title[:50]}...")
            return True
        else:
            print(f"❌ DB 저장 실패: {response}")
            return False
            
    except Exception as e:
        print(f"❌ DB 저장 중 에러: {e}")
        return False