import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from client import init_supabase

def test_supabase_connection():
    """Supabase 연결 테스트"""
    try:
        # Supabase 클라이언트 생성
        supabase = init_supabase()
        
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