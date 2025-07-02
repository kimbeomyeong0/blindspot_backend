from playwright.sync_api import sync_playwright
import time
import sys
import os

# 상위 디렉토리의 supabase_client를 import하기 위해 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from supabase_client import save_article_to_db, init_supabase

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

        for category in categories:
            print(f"\n=== 조선일보 {category['name']} 기사 크롤링 시작 ===")
            page.goto(category['url'])
            time.sleep(3)  # 페이지 로딩 대기
            
            # 더보기 버튼을 여러 번 클릭해서 30개 이상 기사 로드
            click_count = 0
            target_articles = 30
            
            while click_count < 15:  # 최대 15번 더보기 클릭
                try:
                    # 현재 기사 개수 확인 (조선일보 기사 링크 패턴)
                    articles = page.query_selector_all("a[href*='/politics/'], a[href*='/national/'], a[href*='/economy/']")
                    print(f"현재 로드된 기사 개수: {len(articles)}")
                    
                    if len(articles) >= target_articles:
                        print(f"{target_articles}개 이상 기사 로드 완료!")
                        break
                    
                    # 더보기 버튼 찾기 및 클릭 (조선일보 더보기 버튼 셀렉터)
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
                                time.sleep(3)  # 로딩 대기
                                click_count += 1
                                clicked = True
                                break
                        except Exception as e:
                            continue
                    
                    if not clicked:
                        print("더보기 버튼을 찾을 수 없음. 스크롤 시도...")
                        # 스크롤로 추가 콘텐츠 로드 시도
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        time.sleep(2)
                        click_count += 1
                        
                except Exception as e:
                    print(f"더보기 클릭 중 에러: {e}")
                    break
            
            # 기사 링크 수집 (조선일보 URL 패턴)
            article_selectors = [
                f"a[href*='/{category['url'].split('/')[-2]}/']",  # 해당 카테고리 URL 패턴
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
                                    # 상대 URL을 절대 URL로 변환
                                    if href.startswith("/"):
                                        full_url = "https://www.chosun.com" + href
                                    elif href.startswith("https://www.chosun.com"):
                                        full_url = href
                                    else:
                                        continue
                                    
                                    # 해당 카테고리 기사인지 확인
                                    category_path = category['url'].split('/')[-2]  # politics, national, economy
                                    if category_path in full_url and full_url not in visited_urls:
                                        article_urls.append(full_url)
                                        visited_urls.add(full_url)
                                        
                                        if len(article_urls) >= 40:  # 여유있게 40개까지
                                            break
                            except:
                                continue
                        
                        if article_urls:
                            break  # 링크를 찾으면 다른 셀렉터는 시도하지 않음
                except Exception as e:
                    print(f"셀렉터 '{selector}' 처리 중 에러: {e}")
                    continue
            
            print(f"수집된 기사 URL: {len(article_urls)}개")
            
            # 상위 30개 기사만 처리
            target_urls = article_urls[:30]
            article_count = 0
            
            # 각 기사 페이지에서 본문 추출
            for i, article_url in enumerate(target_urls):
                try:
                    print(f"기사 {i+1}/{len(target_urls)} 크롤링 중...")
                    page.goto(article_url)
                    time.sleep(2)
                    
                    # 조선일보 기사 제목과 본문 셀렉터
                    title = page.title() or "제목 없음"
                    
                    # 본문 추출 (조선일보 본문 셀렉터)
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
                        media_outlet="조선일보",
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
            
            print(f"✅ 조선일보 {category['name']} 완료: {article_count}개 수집")
        
        browser.close()
        
        print(f"\n=== 조선일보 총 90개 기사 수집 완료 ===")
        print(" 정치: 30개")
        print(" 사회: 30개")
        print(" 경제: 30개")

if __name__ == "__main__":
    crawl_chosun()
