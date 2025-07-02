import threading
import time
from datetime import datetime
from crawlers.hani_crawler import crawl_hani
from crawlers.kbs_crawler import crawl_kbs
from crawlers.ytn_crawler import crawl_ytn
from crawlers.chosun_crawler import crawl_chosun

def run_crawler_with_timer(crawler_func, crawler_name):
    """개별 크롤러를 실행하고 시간을 측정"""
    print(f"\n🚀 {crawler_name} 크롤링 시작...")
    start_time = time.time()
    
    try:
        articles = crawler_func()
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"✅ {crawler_name} 완료! 소요시간: {duration:.1f}초, 수집기사: {len(articles)}개")
        return articles, duration, None
        
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        print(f"❌ {crawler_name} 실패! 소요시간: {duration:.1f}초, 에러: {str(e)[:100]}")
        return [], duration, str(e)

def crawl_all_parallel():
    """모든 크롤러를 병렬로 실행"""
    print("=" * 60)
    print("🔥 BlindSpot 뉴스 크롤링 시작 (병렬 처리)")
    print("=" * 60)
    
    total_start_time = time.time()
    
    # 크롤러 정보
    crawlers = [
        (crawl_hani, "한겨레"),
        (crawl_kbs, "KBS뉴스"), 
        (crawl_ytn, "YTN"),
        (crawl_chosun, "조선일보")
    ]
    
    # 병렬 실행을 위한 스레드 생성
    threads = []
    results = {}
    
    def thread_wrapper(crawler_func, crawler_name):
        """스레드에서 실행될 함수"""
        result = run_crawler_with_timer(crawler_func, crawler_name)
        results[crawler_name] = result
    
    # 모든 크롤러를 동시에 시작
    for crawler_func, crawler_name in crawlers:
        thread = threading.Thread(
            target=thread_wrapper, 
            args=(crawler_func, crawler_name)
        )
        threads.append(thread)
        thread.start()
    
    # 모든 스레드가 완료될 때까지 대기
    for thread in threads:
        thread.join()
    
    total_end_time = time.time()
    total_duration = total_end_time - total_start_time
    
    print("\n" + "=" * 60)
    print("🏁 전체 크롤링 완료!")
    print("=" * 60)
    
    # 결과 정리
    all_articles = []
    total_articles = 0
    
    for crawler_name in ["한겨레", "KBS뉴스", "YTN", "조선일보"]:
        if crawler_name in results:
            articles, duration, error = results[crawler_name]
            
            if error:
                print(f"❌ {crawler_name}: 실패 (에러: {error[:50]}...)")
            else:
                print(f"✅ {crawler_name}: {len(articles)}개 기사, {duration:.1f}초")
                all_articles.extend(articles)
                total_articles += len(articles)
        else:
            print(f"⚠️  {crawler_name}: 결과 없음")
    
    print(f"\n📊 전체 결과:")
    print(f"   총 수집 기사: {total_articles}개")
    print(f"   총 소요 시간: {total_duration:.1f}초")
    print(f"   평균 속도: {total_articles/total_duration:.1f}개/초")
    
    # 언론사별/카테고리별 통계
    print(f"\n📈 상세 통계:")
    
    stats = {}
    for article in all_articles:
        media = article.get('media_outlet', '알 수 없음')
        category = article.get('category', '알 수 없음')
        
        if media not in stats:
            stats[media] = {}
        if category not in stats[media]:
            stats[media][category] = 0
        stats[media][category] += 1
    
    for media, categories in stats.items():
        print(f"   📰 {media}:")
        for category, count in categories.items():
            print(f"      └─ {category}: {count}개")
    
    return all_articles

if __name__ == "__main__":
    # 시작 시간 기록
    start_timestamp = datetime.now()
    print(f"⏰ 크롤링 시작 시간: {start_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 병렬 크롤링 실행
    articles = crawl_all_parallel()
    
    # 종료 시간 기록
    end_timestamp = datetime.now()
    print(f"⏰ 크롤링 종료 시간: {end_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    
    print(f"\n🎉 BlindSpot 뉴스 크롤링 완료!")
    print(f"📝 수집된 총 기사: {len(articles)}개")
