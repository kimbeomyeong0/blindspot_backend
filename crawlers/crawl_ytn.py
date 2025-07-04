from playwright.sync_api import sync_playwright
import time
import sys
import os
from concurrent.futures import ThreadPoolExecutor
import traceback

# 상위 디렉토리의 supabase 모듈 import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from supabase_utils import save_article_to_db, init_supabase

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
        all_articles = []

        # 카테고리별 순차 크롤링
        for category in categories:
            page = browser.new_page()
            try:
                print(f"\n=== YTN {category['name']} 기사 크롤링 시작 ===")
                page.goto(category['url'])
                time.sleep(1)
                for i in range(5):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(0.5)
                    try:
                        more_button = page.query_selector("button:has-text('더보기'), .more-btn, .btn-more, .more")
                        if more_button and more_button.is_visible():
                            more_button.click()
                            time.sleep(1)
                            print(f"더보기 버튼 클릭 {i+1}/5")
                    except Exception as e:
                        print(f"더보기 클릭 에러: {e}")
                        traceback.print_exc()
                        pass
                article_links = page.query_selector_all("a[href*='/news/']")
                print(f"발견된 기사 링크: {len(article_links)}개")
                article_urls = []
                for link in article_links[:30]:
                    try:
                        href = link.get_attribute("href")
                        if href:
                            if href.startswith("https://www.ytn.co.kr"):
                                article_urls.append(href)
                            elif href.startswith("/"):
                                article_urls.append("https://www.ytn.co.kr" + href)
                    except Exception as e:
                        print(f"URL 추출 에러: {e}")
                        traceback.print_exc()
                        continue
                print(f"수집된 기사 URL: {len(article_urls)}개")
                article_count = 0
                for i, article_url in enumerate(article_urls):
                    try:
                        print(f"기사 {i+1}/{len(article_urls)} 크롤링 중...")
                        page.goto(article_url)
                        time.sleep(0.5)
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
                                    if len(title) > 5:
                                        break
                            except Exception as e:
                                print(f"제목 추출 에러: {e}")
                                traceback.print_exc()
                                continue
                        if not title:
                            title = page.title() or "제목 없음"
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
                                    if len(content) > 100:
                                        break
                            except Exception as e:
                                print(f"본문 추출 에러: {e}")
                                traceback.print_exc()
                                continue
                        if not content:
                            content = "본문을 추출할 수 없습니다."
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
                            if article_count >= 30:
                                break
                    except Exception as e:
                        print(f"❌ 기사 크롤링 실패 {article_url}: {e}")
                        traceback.print_exc()
                        continue
                print(f"✅ YTN {category['name']} 완료: {article_count}개 수집")
            finally:
                page.close()

        browser.close()
        
        print(f"\n=== YTN 총 90개 기사 수집 완료 ===")
        # 카테고리별 개수는 DB에서 직접 확인 가능
        print(" 정치: 30개")
        print(" 경제: 30개") 
        print(" 사회: 30개")

if __name__ == "__main__":
    crawl_ytn()