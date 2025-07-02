from playwright.sync_api import sync_playwright
import time
import sys
import os

# 상위 디렉토리의 supabase_client 모듈 import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from supabase_client import get_supabase_client, save_article_to_db

def crawl_hani():
    # 한겨레 카테고리별 URL
    categories = [
        {"name": "정치", "prefix": "https://www.hani.co.kr/arti/politics"},
        {"name": "경제", "prefix": "https://www.hani.co.kr/arti/economy"},
        {"name": "사회", "prefix": "https://www.hani.co.kr/arti/society"},
    ]

    # Supabase 클라이언트 초기화
    supabase = get_supabase_client()
    print("🔗 Supabase 연결 완료")

    with sync_playwright() as p:
        # 브라우저 최적화 옵션 적용
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage', 
                '--disable-images',
                '--disable-plugins',
                '--disable-extensions',
                '--no-first-run',
                '--disable-default-apps'
            ]
        )
        page = browser.new_page()
        all_articles = []

        for category in categories:
            print(f"=== 한겨레 {category['name']} 기사 크롤링 시작 ===")
            articles_collected = 0
            page_num = 1
            visited_urls = set()
            
            while articles_collected < 30 and page_num <= 5:  # 최대 5페이지
                url = f"{category['prefix']}?page={page_num}"
                print(f"페이지 이동: {url}")
                
                try:
                    page.goto(url, wait_until='domcontentloaded')
                    time.sleep(2)
                    
                    # 현재 페이지에서 모든 기사 URL을 먼저 추출
                    links = page.query_selector_all("article a")
                    article_urls = []
                    
                    for link in links:
                        try:
                            href = link.get_attribute("href")
                            if href and href.startswith("/arti/"):
                                full_url = "https://www.hani.co.kr" + href
                                if full_url not in visited_urls:
                                    article_urls.append(full_url)
                                    visited_urls.add(full_url)
                        except:
                            continue
                    
                    print(f"이 페이지에서 {len(article_urls)}개 새로운 기사 URL 발견")
                    
                    # 추출된 URL들로 개별 기사 수집
                    for article_url in article_urls:
                        if articles_collected >= 30:
                            break
                            
                        try:
                            page.goto(article_url, wait_until='domcontentloaded')
                            time.sleep(1)
                            
                            title = page.title()
                            content = ""
                            
                            try:
                                content_element = page.query_selector(".article-text")
                                if content_element:
                                    content = content_element.inner_text()
                            except:
                                pass
                            
                            if title and content:
                                article_data = {
                                    "title": title,
                                    "content": content,
                                    "category": category["name"],
                                    "url": article_url,
                                    "media_outlet": "한겨레",
                                    "bias": "left"
                                }
                                
                                # 🔥 Supabase에 저장
                                if save_article_to_db(supabase, article_data):
                                    all_articles.append(article_data)
                                    articles_collected += 1
                                    print(f"✅ {articles_collected}번째 기사 저장: {title[:50]}...")
                                else:
                                    print(f"❌ DB 저장 실패: {title[:50]}...")
                            
                        except Exception as e:
                            print(f"❌ 기사 처리 중 에러 (무시): {str(e)[:50]}...")
                            continue
                    
                    page_num += 1
                    
                except Exception as e:
                    print(f"페이지 로딩 에러: {e}")
                    break
            
            print(f"✅ 한겨레 {category['name']} 완료: {articles_collected}개 수집")

        browser.close()
        return all_articles

# 테스트용 실행
if __name__ == "__main__":
    articles = crawl_hani()
    print(f"\n=== 한겨레 총 {len(articles)}개 기사 수집 완료 ===")
    
    # 카테고리별 개수 확인
    categories_count = {}
    for article in articles:
        cat = article['category']
        categories_count[cat] = categories_count.get(cat, 0) + 1
    
    for cat, count in categories_count.items():
        print(f" {cat}: {count}개")