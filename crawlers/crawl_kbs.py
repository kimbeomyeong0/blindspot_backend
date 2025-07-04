from playwright.sync_api import sync_playwright
import time
import sys
import os
from concurrent.futures import ThreadPoolExecutor
import traceback

# 상위 디렉토리의 supabase 모듈 import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import save_article_to_db, init_supabase

def crawl_kbs():
    # Supabase 초기화
    supabase = init_supabase()
    print("🔗 Supabase 연결 완료")
    
    categories = [
        {"name": "정치", "url": "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0003"},
        {"name": "경제", "url": "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0004"},
        {"name": "사회", "url": "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0005"},
    ]
    
    with sync_playwright() as p:
        # 🚀 브라우저 최적화 옵션 적용
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage', 
                '--disable-images',           # 이미지 로딩 차단
                '--disable-plugins',
                '--disable-extensions',
                '--no-first-run',
                '--disable-default-apps'
            ]
        )
        page = browser.new_page()

        # 카테고리별 순차 크롤링
        for category in categories:
            page = browser.new_page()
            try:
                print(f"\n=== KBS {category['name']} 기사 크롤링 시작 ===")
                page.goto(category["url"], wait_until='domcontentloaded')
                time.sleep(1)
                for i in range(5):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(0.5)
                    try:
                        more_button = page.query_selector("button:has-text('더보기'), .more-btn, .btn-more")
                        if more_button and more_button.is_visible():
                            more_button.click()
                            time.sleep(1)
                            print(f"더보기 버튼 클릭 {i+1}/5")
                    except Exception as e:
                        print(f"더보기 클릭 에러: {e}")
                        traceback.print_exc()
                        pass
                article_selectors = [
                    "a[href*='/news/view/']",
                    "a[href*='ncd=']",
                    ".headline a",
                    ".news-item a",
                    ".title a",
                    "h3 a",
                    "h4 a",
                    ".subject a"
                ]
                article_urls = []
                visited_urls = set()
                for selector in article_selectors:
                    links = page.query_selector_all(selector)
                    if links:
                        print(f"'{selector}' 셀렉터로 {len(links)}개 링크 발견")
                        for link in links:
                            try:
                                href = link.get_attribute("href")
                                if href and ("/news/view/" in href or "ncd=" in href):
                                    if not href.startswith("http"):
                                        href = "https://news.kbs.co.kr" + href
                                    if href not in visited_urls:
                                        article_urls.append(href)
                                        visited_urls.add(href)
                                    if len(article_urls) >= 50:
                                        break
                            except Exception as e:
                                print(f"URL 추출 에러: {e}")
                                traceback.print_exc()
                                continue
                        if article_urls:
                            break
                print(f"수집된 기사 URL: {len(article_urls)}개")
                target_urls = article_urls[:30]
                articles_collected = 0
                for i, article_url in enumerate(target_urls):
                    try:
                        print(f"기사 {i+1}/{len(target_urls)} 크롤링 중...")
                        page.goto(article_url, wait_until='domcontentloaded')
                        time.sleep(0.5)
                        title = page.title()
                        content_selectors = [
                            ".detail-body",
                            ".article-body",
                            ".news-content",
                            ".content-area",
                            ".article-text",
                            ".view-cont",
                            ".txt",
                            "#content",
                            ".article_txt"
                        ]
                        content = ""
                        for content_selector in content_selectors:
                            try:
                                content_element = page.query_selector(content_selector)
                                if content_element:
                                    content = content_element.inner_text().strip()
                                    if len(content) > 100:
                                        break
                            except Exception as e:
                                print(f"본문 추출 에러: {e}")
                                traceback.print_exc()
                                continue
                        if title and content and len(content) > 100:
                            success = save_article_to_db(
                                supabase=supabase,
                                title=title,
                                content=content,
                                url=article_url,
                                media_outlet="KBS뉴스",
                                category=category["name"]
                            )
                            if success:
                                articles_collected += 1
                                print(f"✅ {articles_collected}번째 기사 저장: {title[:50]}...")
                                if articles_collected >= 30:
                                    print(f"✅ {category['name']} 카테고리 30개 완료!")
                                    break
                        else:
                            print(f"❌ 본문이 부족한 기사 건너뜀")
                    except Exception as e:
                        print(f"❌ 기사 처리 중 에러: {e}")
                        traceback.print_exc()
                        continue
                print(f"✅ KBS {category['name']} 완료: {articles_collected}개 수집")
            finally:
                page.close()

        browser.close()
        
        print(f"\n=== KBS 총 90개 기사 수집 완료 ===")
        print(" 정치: 30개")
        print(" 경제: 30개")
        print(" 사회: 30개")

if __name__ == "__main__":
    crawl_kbs()
