from .client import get_supabase_client, get_media_outlet_id, get_category_id
from datetime import datetime

def save_article_to_db(supabase, article_data=None, **kwargs):
    """기사를 Supabase에 저장 (모든 방식 지원)"""
    try:
        # 방식 1: save_article_to_db(supabase, article_data)
        if article_data is not None and isinstance(article_data, dict):
            title = article_data.get('title') if article_data.get('title') is not None else None
            content = article_data.get('content') if article_data.get('content') is not None else None
            url = article_data.get('url') if article_data.get('url') is not None else None
            media_outlet = article_data.get('media_outlet') if article_data.get('media_outlet') is not None else None
            category = article_data.get('category') if article_data.get('category') is not None else None
        # 방식 2: save_article_to_db(supabase, title=title, content=content, ...)
        else:
            title = kwargs.get('title') if kwargs.get('title') is not None else None
            content = kwargs.get('content') if kwargs.get('content') is not None else None
            url = kwargs.get('url') if kwargs.get('url') is not None else None
            media_outlet = kwargs.get('media_outlet') if kwargs.get('media_outlet') is not None else None
            category = kwargs.get('category') if kwargs.get('category') is not None else None
        
        # 필수 데이터 확인
        if not all([title, content, url, media_outlet, category]):
            print(f"❌ 필수 데이터 누락: title={bool(title)}, content={bool(content)}, url={bool(url)}, media_outlet={bool(media_outlet)}, category={bool(category)}")
            return False
        
        # 중복 URL 체크
        existing = supabase.table('articles').select("id").eq('url', url).execute()
        if existing.data and isinstance(existing.data, list) and existing.data:
            print(f"⚠️ 이미 존재하는 URL (건너뜀): {title[:30]}...")
            return False
        
        # 언론사 ID 조회
        if media_outlet is None:
            print(f"❌ 언론사 정보 누락")
            return False
        media_outlet_id = get_media_outlet_id(supabase, media_outlet)
        if not media_outlet_id:
            return False
        
        # 카테고리 ID 조회
        if category is None:
            print(f"❌ 카테고리 정보 누락")
            return False
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

def save_cluster_to_db(supabase, cluster_data):
    """클러스터 분석 결과를 Supabase에 저장"""
    try:
        if not cluster_data:
            print("[경고] cluster_data가 None입니다. 저장을 건너뜁니다.")
            return
        cluster_id = cluster_data.get('cluster_id')
        topic = cluster_data.get('topic')
        summary = cluster_data.get('summary')
        article_count = cluster_data.get('article_count', 0)
        category = cluster_data.get('category')
        print(f"[DB 저장 함수 진입] category={category}, cluster_id={cluster_id}, topic={topic}, article_count={article_count}")
        # 필수 데이터 확인
        if cluster_id is None or not topic:
            print(f"❌ 클러스터 데이터 누락: cluster_id={cluster_id}, topic={bool(topic)}")
            return False
        # 중복 클러스터 체크 (같은 cluster_id가 있는지)
        existing = supabase.table('clusters').select("id").eq('cluster_id', cluster_id).execute()
        if existing.data and isinstance(existing.data, list) and existing.data:
            print(f"⚠️ 이미 존재하는 클러스터 (업데이트): cluster_id={cluster_id}")
            db_data = {
                "cluster_id": cluster_id,
                "category": category,
                "topic": topic,
                "summary": summary,
                "article_count": article_count,
                "updated_at": "NOW()"
            }
            try:
                response = supabase.table('clusters').update(db_data).eq('cluster_id', cluster_id).execute()
                print(f"[DB 저장 성공] category={category}, cluster_id={cluster_id}")
            except Exception as e:
                print(f"[DB 저장 실패] category={category}, cluster_id={cluster_id}, error={e}")
                raise
        else:
            db_data = {
                "cluster_id": cluster_id,
                "category": category,
                "topic": topic,
                "summary": summary,
                "article_count": article_count,
                "created_at": "NOW()",
                "updated_at": "NOW()"
            }
            try:
                response = supabase.table('clusters').insert(db_data).execute()
                print(f"[DB 저장 성공] category={category}, cluster_id={cluster_id}")
            except Exception as e:
                print(f"[DB 저장 실패] category={category}, cluster_id={cluster_id}, error={e}")
                raise
        print(f"🔍 [디버깅] DB 저장 데이터:")
        print(f"  - db_data: {db_data}")
        if response is not None and hasattr(response, 'data') and response.data:
            topic_str = str(topic)[:30] if topic else ''
            summary_str = str(summary) if summary else ''
            print(f"✅ 클러스터 저장 성공: cluster_id={cluster_id}, topic={topic_str}...")
            print(f"🔍 [디버깅] 저장된 summary: '{summary_str}'")
            return True
        else:
            print(f"❌ 클러스터 저장 실패: {response}")
            return False
    except Exception as e:
        print(f"❌ 클러스터 저장 중 에러: {e}")
        return False

def save_cluster_articles_to_db(supabase, cluster_id, article_ids):
    """클러스터에 속한 기사들의 관계를 저장"""
    try:
        if not cluster_id or not article_ids:
            print(f"[경고] cluster_articles 저장 건너뜀: cluster_id={cluster_id}, article_ids={article_ids}")
            return
        
        # 기존 관계 삭제 (같은 cluster_id의 모든 관계)
        supabase.table('cluster_articles').delete().eq('cluster_id', cluster_id).execute()
        
        # 새로운 관계 추가
        cluster_article_data = []
        for article_id in article_ids:
            cluster_article_data.append({
                "cluster_id": cluster_id,
                "article_id": article_id
            })
        
        if cluster_article_data:
            response = supabase.table('cluster_articles').insert(cluster_article_data).execute()
            if response.data:
                print(f"✅ 클러스터-기사 관계 저장 성공: cluster_id={cluster_id}, 기사 {len(article_ids)}개")
                return True
            else:
                print(f"❌ 클러스터-기사 관계 저장 실패: {response}")
                return False
        else:
            print(f"⚠️ 저장할 기사가 없음: cluster_id={cluster_id}")
            return False
            
    except Exception as e:
        print(f"❌ 클러스터-기사 관계 저장 중 에러: {e}")
        return False

def save_analysis_session_to_db(supabase, session_data):
    """분석 세션 정보를 저장"""
    try:
        session_name = session_data.get('session_name', f"분석_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        total_articles = session_data.get('total_articles', 0)
        cluster_count = session_data.get('cluster_count', 0)
        analysis_summary = session_data.get('analysis_summary', '')
        
        db_data = {
            "session_name": session_name,
            "total_articles": total_articles,
            "cluster_count": cluster_count,
            "analysis_summary": analysis_summary,
            "created_at": "NOW()"
        }
        
        response = supabase.table('analysis_sessions').insert(db_data).execute()
        
        if response.data:
            print(f"✅ 분석 세션 저장 성공: {session_name}")
            # response.data가 None이거나 list가 아닐 수 있으니 방어적으로 처리
            if isinstance(response.data, list) and response.data and isinstance(response.data[0], dict) and 'id' in response.data[0]:
                return response.data[0]['id']  # 세션 ID 반환
            else:
                return None
        else:
            print(f"❌ 분석 세션 저장 실패: {response}")
            return None
            
    except Exception as e:
        print(f"❌ 분석 세션 저장 중 에러: {e}")
        return None

def load_articles_from_db(supabase):
    """Supabase에서 모든 기사 데이터 로드"""
    try:
        # 기사와 언론사, 카테고리 정보를 JOIN해서 가져오기
        response = supabase.table('articles').select("""
            id,
            title,
            content,
            url,
            published_at,
            media_outlets(name, bias),
            categories(name)
        """).execute()
        
        print(f"📊 총 {len(response.data)}개 기사 로드 완료")
        return response.data
        
    except Exception as e:
        print(f"❌ 기사 로드 실패: {e}")
        return []

def load_clusters_from_db(supabase):
    """Supabase에서 클러스터 데이터 로드"""
    try:
        response = supabase.table('clusters').select("""
            id,
            cluster_id,
            topic,
            summary,
            article_count,
            created_at,
            updated_at
        """).order('cluster_id').execute()
        
        print(f"📊 총 {len(response.data)}개 클러스터 로드 완료")
        return response.data
        
    except Exception as e:
        print(f"❌ 클러스터 로드 실패: {e}")
        return [] 