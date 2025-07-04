from playwright.sync_api import sync_playwright
import time
import sys
import os
from concurrent.futures import ThreadPoolExecutor
import traceback

# 상위 디렉토리의 supabase 모듈 import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import save_article_to_db, init_supabase

def crawl_chosun():
    # Supabase 초기화
    supabase = init_supabase()
    print("🔗 Supabase 연결 완료")
    
    # 조선일보 카테고리별 URL
    categories = [
        {"name": "정치", "url": "https://www.chosun.com/politics/"},
        {"name": "사회", "url": "https://www.chosun.com/national/"},
        {"name": "경제", "url": "https://www.chosun.com/economy/"},
    ]
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage', 
                '--disable-images',           # 이미지 로딩 차단
                '--disable-javascript',       # JS 비활성화 (필요시)
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
                print(f"\n=== 조선일보 {category['name']} 기사 크롤링 시작 ===")
                page.goto(category['url'])
                time.sleep(1)
                click_count = 0
                target_articles = 30
                while click_count < 15:
                    try:
                        articles = page.query_selector_all("a[href*='/politics/'], a[href*='/national/'], a[href*='/economy/']")
                        print(f"현재 로드된 기사 개수: {len(articles)}")
                        if len(articles) >= target_articles:
                            print(f"{target_articles}개 이상 기사 로드 완료!")
                            break
                        more_button_selectors = [
                            ".more-news-btn",
                            ".btn-more",
                            ".load-more",
                            ".more-btn",
                            "button:has-text('더보기')",
                            "a:has-text('더보기')",
                            ".story-card-more",
                            ".list-more"
                        ]
                        clicked = False
                        for selector in more_button_selectors:
                            try:
                                more_button = page.query_selector(selector)
                                if more_button and more_button.is_visible():
                                    print(f"더보기 버튼 클릭 {click_count + 1}번째... (셀렉터: {selector})")
                                    more_button.click()
                                    time.sleep(1)
                                    click_count += 1
                                    clicked = True
                                    break
                            except Exception as e:
                                print(f"더보기 클릭 에러: {e}")
                                traceback.print_exc()
                                continue
                        if not clicked:
                            print("더보기 버튼을 찾을 수 없음. 스크롤 시도...")
                            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                            time.sleep(0.5)
                            click_count += 1
                    except Exception as e:
                        print(f"더보기 클릭 중 에러: {e}")
                        traceback.print_exc()
                        break
                article_selectors = [
                    f"a[href*='/{category['url'].split('/')[-2]}/']",
                    ".story-card a",
                    ".headline a",
                    ".news-item a",
                    ".article-link",
                    "h3 a",
                    "h4 a"
                ]
                article_urls = []
                visited_urls = set()
                for selector in article_selectors:
                    try:
                        links = page.query_selector_all(selector)
                        if links:
                            print(f"'{selector}' 셀렉터로 {len(links)}개 링크 발견")
                            for link in links:
                                try:
                                    href = link.get_attribute("href")
                                    if href:
                                        if href.startswith("/"):
                                            full_url = "https://www.chosun.com" + href
                                        elif href.startswith("https://www.chosun.com"):
                                            full_url = href
                                        else:
                                            continue
                                        category_path = category['url'].split('/')[-2]
                                        if category_path in full_url and full_url not in visited_urls:
                                            article_urls.append(full_url)
                                            visited_urls.add(full_url)
                                            if len(article_urls) >= 40:
                                                break
                                except Exception as e:
                                    print(f"URL 추출 에러: {e}")
                                    traceback.print_exc()
                                    continue
                            if article_urls:
                                break
                    except Exception as e:
                        print(f"셀렉터 '{selector}' 처리 중 에러: {e}")
                        traceback.print_exc()
                        continue
                print(f"수집된 기사 URL: {len(article_urls)}개")
                target_urls = article_urls[:30]
                article_count = 0
                for i, article_url in enumerate(target_urls):
                    try:
                        print(f"기사 {i+1}/{len(target_urls)} 크롤링 중...")
                        page.goto(article_url)
                        time.sleep(0.5)
                        title = page.title() or "제목 없음"
                        content_selectors = [
                            ".article-body",
                            ".news-article-body",
                            ".story-content",
                            "#article-body",
                            ".article-content",
                            ".story-body",
                            ".entry-content"
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
                        if not content:
                            content = "본문을 추출할 수 없습니다."
                        success = save_article_to_db(
                            supabase=supabase,
                            title=title,
                            content=content,
                            url=article_url,
                            media_outlet="조선일보",
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
                print(f"✅ 조선일보 {category['name']} 완료: {article_count}개 수집")
            finally:
                page.close()

        browser.close()
        
        print(f"\n=== 조선일보 총 90개 기사 수집 완료 ===")
        print(" 정치: 30개")
        print(" 사회: 30개")
        print(" 경제: 30개")

if __name__ == "__main__":
    crawl_chosun()
