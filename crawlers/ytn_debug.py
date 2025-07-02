from playwright.sync_api import sync_playwright
import time

def debug_ytn():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # 브라우저 창 보기
        page = browser.new_page()
        
        # YTN 정치 페이지로 이동
        page.goto("https://www.ytn.co.kr/news/list.php?mcd=0101")
        time.sleep(5)
        
        print("=== 페이지 제목 ===")
        print(page.title())
        
        # 여러 가능한 셀렉터들 시도해보기
        selectors = [
            "ul.list > li",
            ".list li", 
            ".news-list li",
            ".article-list li",
            "li",
            "a[href*='/news/']",
            ".headline",
            ".title",
            "h3", 
            "h4"
        ]
        
        for selector in selectors:
            try:
                elements = page.query_selector_all(selector)
                print(f"'{selector}': {len(elements)}개 발견")
                
                if len(elements) > 0 and len(elements) < 50:  # 너무 많지 않은 것들만
                    first_element = elements[0]
                    print(f"  첫 번째 요소 텍스트: {first_element.inner_text()[:100]}...")
                    
                    # a 태그가 있는지 확인
                    link = first_element.query_selector("a")
                    if link:
                        href = link.get_attribute("href")
                        print(f"  첫 번째 링크: {href}")
                    
            except Exception as e:
                print(f"'{selector}': 에러 - {e}")
        
        input("엔터를 누르면 브라우저가 닫힙니다...")
        browser.close()

if __name__ == "__main__":
    debug_ytn() 