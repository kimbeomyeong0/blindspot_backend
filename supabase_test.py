from supabase import create_client, Client

# Supabase 연결 정보
SUPABASE_URL = "https://grcvxnnkfpewzejifesu.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdyY3Z4bm5rZnBld3plamlmZXN1Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MTQ3MTQ2MSwiZXhwIjoyMDY3MDQ3NDYxfQ.PHWwtDU5xr-QkM_R3oGWu-Cmyseiv253SwJw8rcN7ug"

def test_supabase_connection():
    """Supabase 연결 테스트"""
    try:
        # Supabase 클라이언트 생성
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        print("🔗 Supabase 연결 성공!")
        
        # 언론사 테이블 조회 테스트
        response = supabase.table('media_outlets').select("*").execute()
        print(f"📰 언론사 개수: {len(response.data)}개")
        
        for outlet in response.data:
            print(f"   - {outlet['name']} ({outlet['bias']})")
        
        # 카테고리 테이블 조회 테스트  
        response = supabase.table('categories').select("*").execute()
        print(f"📁 카테고리 개수: {len(response.data)}개")
        
        for category in response.data:
            print(f"   - {category['name']} ({category['ascii']})")
        
        # 기사 테이블 조회 테스트 (비어있어야 정상)
        response = supabase.table('articles').select("*").execute()
        print(f"📄 기존 기사 개수: {len(response.data)}개")
            
        return True
        
    except Exception as e:
        print(f"❌ Supabase 연결 실패: {e}")
        return False

if __name__ == "__main__":
    test_supabase_connection()