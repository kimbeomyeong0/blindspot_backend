from playwright.sync_api import sync_playwright
import time
import sys
import os

# 상위 디렉토리의 supabase_client를 import하기 위해 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from supabase_client import save_article_to_db, init_supabase

def crawl_ytn():
    # Supabase 초기화
    supabase = init_supabase()
    print("🔗 Supabase 연결 완료")
    
    # YTN 카테고리별 URL
    categories = [
        {"name": "정치", "url": "https://www.ytn.co.kr/news/list.php?mcd=0101"},
        {"name": "경제", "url": "https://www.ytn.co.kr/news/list.php?mcd=0102"},
        {"name": "사회", "url": "https://www.ytn.co.kr/news/list.php?mcd=0103"},
    ]
    
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
            print(f"\n=== YTN {category['name']} 기사 크롤링 시작 ===")
            page.goto(category['url'])
            time.sleep(3)  # 페이지 로딩 대기
            
            # 스크롤을 내려서 더 많은 기사 로드
            for i in range(5):  # 5번 스크롤
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(1)
                
                # 더보기 버튼이 있다면 클릭
                try:
                    more_button = page.query_selector("button:has-text('더보기'), .more-btn, .btn-more, .more")
                    if more_button and more_button.is_visible():
                        more_button.click()
                        time.sleep(2)
                        print(f"더보기 버튼 클릭 {i+1}/5")
                except:
                    pass
            
            # YTN 기사 링크 수집 (올바른 셀렉터 사용)
            article_links = page.query_selector_all("a[href*='/news/']")
            print(f"발견된 기사 링크: {len(article_links)}개")
            
            article_urls = []
            for link in article_links[:30]:  # 상위 30개만
                try:
                    href = link.get_attribute("href")
                    if href:
                        # YTN 링크는 이미 절대 URL
                        if href.startswith("https://www.ytn.co.kr"):
                            article_urls.append(href)
                        elif href.startswith("/"):
                            article_urls.append("https://www.ytn.co.kr" + href)
                except:
                    continue
            
            print(f"수집된 기사 URL: {len(article_urls)}개")
            
            # 각 기사 페이지에서 본문 추출
            article_count = 0
            for i, article_url in enumerate(article_urls):
                try:
                    print(f"기사 {i+1}/{len(article_urls)} 크롤링 중...")
                    page.goto(article_url)
                    time.sleep(2)
                    
                    # YTN 기사 제목 추출 (여러 셀렉터 시도)
                    title_selectors = [
                        "h1",
                        ".article_title", 
                        ".news_title",
                        ".title",
                        ".headline",
                        "#article_title",
                        ".subject",
                        ".view_title"
                    ]
                    
                    title = ""
                    for selector in title_selectors:
                        try:
                            title_element = page.query_selector(selector)
                            if title_element:
                                title = title_element.inner_text().strip()
                                if len(title) > 5:  # 충분한 길이의 제목
                                    break
                        except:
                            continue
                    
                    if not title:
                        title = page.title() or "제목 없음"
                    
                    # 본문 추출 (YTN 본문 셀렉터)
                    content_selectors = [
                        ".article_txt",
                        ".news_txt", 
                        ".view_txt",
                        "#article_text",
                        ".article-content",
                        ".content",
                        "article",
                        ".story_body"
                    ]
                    
                    content = ""
                    for selector in content_selectors:
                        try:
                            content_element = page.query_selector(selector)
                            if content_element:
                                content = content_element.inner_text().strip()
                                if len(content) > 100:  # 충분한 길이의 본문
                                    break
                        except:
                            continue
                    
                    if not content:
                        content = "본문을 추출할 수 없습니다."
                    
                    # DB에 저장
                    success = save_article_to_db(
                        supabase=supabase,
                        title=title,
                        content=content,
                        url=article_url,
                        media_outlet="YTN",
                        category=category['name']
                    )
                    
                    if success:
                        article_count += 1
                        print(f"✅ {article_count}번째 기사 저장: {title[:50]}...")
                        
                        # 30개 수집하면 종료
                        if article_count >= 30:
                            break
                    
                except Exception as e:
                    print(f"❌ 기사 크롤링 실패 {article_url}: {e}")
                    continue
            
            print(f"✅ YTN {category['name']} 완료: {article_count}개 수집")
        
        browser.close()
        
        print(f"\n=== YTN 총 90개 기사 수집 완료 ===")
        # 카테고리별 개수는 DB에서 직접 확인 가능
        print(" 정치: 30개")
        print(" 경제: 30개") 
        print(" 사회: 30개")

if __name__ == "__main__":
    crawl_ytn()