import os
from dotenv import load_dotenv
import openai
from db import init_supabase, load_articles_from_db, save_cluster_to_db, save_cluster_articles_to_db, save_analysis_session_to_db
from analyzer import cluster_articles, analyze_cluster_topics, calculate_all_clusters_bias
from datetime import datetime
from collections import Counter, defaultdict
from utils import save_markdown_report

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
supabase = init_supabase()
openai_client = openai.OpenAI(api_key=api_key)
openai_model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

# 1. DB에서 기사 불러오기
articles = load_articles_from_db(supabase)
print(f"기사 {len(articles)}개 불러옴")

if not articles:
    print("DB에 기사가 없습니다. 테스트를 종료합니다.")
    exit()

# 2. 카테고리별로 기사 분리
articles_by_category = {}
for article in articles:
    # 실제 구조에 맞게 category 이름 추출
    category = None
    if 'categories' in article and isinstance(article['categories'], dict):
        category = article['categories'].get('name')
    elif 'category' in article:
        category = article['category']
    if category:
        articles_by_category.setdefault(category, []).append(article)

print(f"[DEBUG] articles_by_category keys: {list(articles_by_category.keys())}")

# 최적 클러스터 수 계산 함수 (pipeline.py와 동일)
def calculate_optimal_clusters(article_count):
    if article_count < 30:
        return 3
    elif article_count < 60:
        return 5
    elif article_count < 120:
        return 8
    elif article_count < 200:
        return 10
    else:
        return min(15, max(8, article_count // 25))  # 기사 25개당 1개, 최대 15개 제한

MIN_ARTICLES = 3
report_clusters = []
all_article_ids = set()
article_count_total = 0
for category, articles_in_cat in articles_by_category.items():
    print(f"[DEBUG] 현재 카테고리: {category}, 기사 수: {len(articles_in_cat)}")
    if len(articles_in_cat) < MIN_ARTICLES:
        print(f"⚠️ [{category}] 기사 수 {len(articles_in_cat)}개로 군집화 생략 (MIN_ARTICLES={MIN_ARTICLES})")
        continue
    print(f"[DEBUG] [{category}] 클러스터링 및 DB 저장 시도")
    n_cat_clusters = calculate_optimal_clusters(len(articles_in_cat))
    print(f"[DEBUG] {category} n_clusters: {n_cat_clusters}")
    result = cluster_articles(openai_client, articles_in_cat, n_cat_clusters)
    if result is None:
        print(f"{category} 클러스터링 실패")
        continue
    clustered_articles, cluster_centers = result
    print(f"[DEBUG] {category} 클러스터 개수: {n_cat_clusters}, 실제 클러스터링된 기사 수: {len(clustered_articles)}")
    # 클러스터별로 기사 리스트로 변환
    clusters_dict = {}
    for article in clustered_articles:
        cid = article['cluster_id']
        if cid not in clusters_dict:
            clusters_dict[cid] = []
        clusters_dict[cid].append(article)
    cluster_topics = analyze_cluster_topics(openai_client, clustered_articles)
    print(f"\n🔍 [디버깅] analyze_cluster_topics 반환값:")
    for cluster_id, cluster_info in cluster_topics.items():
        print(f"  - cluster_id {cluster_id}:")
        print(f"    - topic_analysis: {cluster_info.get('topic_analysis', '')[:50]}...")
        print(f"    - summary: '{cluster_info.get('summary', '')}'")
        print(f"    - keywords: {cluster_info.get('keywords', [])}")
    
    # 편향성 계산
    cluster_bias_analysis = calculate_all_clusters_bias(clustered_articles)
    
    for cluster_id, articles_in_cluster in clusters_dict.items():
        unique_cluster_id = f"{category}_{cluster_id}"
        print(f"[DB 저장 시도] category={category}, cluster_id={unique_cluster_id}, article_count={len(articles_in_cluster)}")
        cluster_info = cluster_topics.get(cluster_id, {})
        if not cluster_info.get('summary'):
            print(f"❌ 파싱 실패: cluster_id={unique_cluster_id}, summary='{cluster_info.get('summary')}'")
            continue
        # 편향성 정보 가져오기
        bias_info = cluster_bias_analysis.get(cluster_id, {}).get('bias')
        
        cluster_data = {
            'cluster_id': unique_cluster_id,
            'category': category,
            'topic': cluster_info.get('topic_analysis', f'클러스터 {cluster_id}'),
            'summary': cluster_info.get('summary', ''),
            'article_count': len(articles_in_cluster),
            'bias': bias_info  # 편향성 정보 추가
        }
        print(f"🔍 [디버깅] 최종 cluster_data:")
        print(f"  - cluster_id: {cluster_data['cluster_id']}")
        print(f"  - category: {cluster_data['category']}")
        print(f"  - topic: {str(cluster_data['topic'])[:50]}...")
        print(f"  - summary: '{cluster_data['summary']}'")
        print(f"  - article_count: {cluster_data['article_count']}")
        print("저장 시도:", cluster_data)
        print(f"클러스터 {unique_cluster_id} 예시:", articles_in_cluster[:1])
        print("타입:", type(articles_in_cluster))
        save_cluster_to_db(supabase, cluster_data)
        article_ids = [a.get('id') for a in articles_in_cluster if a.get('id')]
        if article_ids:
            save_cluster_articles_to_db(supabase, unique_cluster_id, article_ids)
        # 언론사/편향 집계
        media_counter = Counter()
        bias_counter = Counter()
        media_bias_map = defaultdict(str)
        for a in articles_in_cluster:
            media = None
            bias = None
            if 'media_outlets' in a and isinstance(a['media_outlets'], dict):
                media = a['media_outlets'].get('name')
                bias = a['media_outlets'].get('bias')
            if not media and 'media' in a:
                media = a['media']
            if not bias and 'bias' in a:
                bias = a['bias']
            if media:
                media_counter[media] += 1
                if bias:
                    media_bias_map[media] = bias
            if bias:
                bias_counter[bias] += 1
        # bias 판정
        total = sum(bias_counter.values())
        bias_pct = {k: (v, v/total*100 if total else 0) for k, v in bias_counter.items()}
        # 편향 판정 로직
        bias_judgement = '⚖️ 균형적 보도'
        if len(bias_counter) == 1:
            if 'left' in bias_counter:
                bias_judgement = '🔴 좌편향 우세'
            elif 'right' in bias_counter:
                bias_judgement = '🔵 우편향 우세'
            elif 'center' in bias_counter:
                bias_judgement = '⚪ 중립 우세'
        elif bias_counter:
            max_bias, max_count = bias_counter.most_common(1)[0]
            max_pct = bias_pct[max_bias][1]
            if max_pct >= 55:
                if max_bias == 'left':
                    bias_judgement = '🔴 좌편향 우세'
                elif max_bias == 'right':
                    bias_judgement = '🔵 우편향 우세'
                elif max_bias == 'center':
                    bias_judgement = '⚪ 중립 우세'
        # 키워드/분야 추출(있으면)
        topic = cluster_data['topic']
        summary = cluster_data['summary']
        keywords = cluster_info.get('keywords', None)
        field = cluster_info.get('분야', None) or cluster_info.get('field', None) or category
        # 기사 ID 집계
        all_article_ids.update(article_ids)
        article_count_total += len(articles_in_cluster)
        # 레포트용 데이터 누적
        report_clusters.append({
            'cluster_id': cluster_id,
            'topic': topic,
            'summary': summary,
            'keywords': keywords,
            'field': field,
            'category': category,
            'article_count': len(articles_in_cluster),
            'media_counter': dict(media_counter),
            'media_bias_map': dict(media_bias_map),
            'bias_counter': dict(bias_counter),
            'bias_pct': bias_pct,
            'bias_judgement': bias_judgement,
            'article_ids': article_ids
        })

# 모든 카테고리/클러스터 저장 후 markdown 리포트 저장
if report_clusters:
    save_markdown_report(report_clusters, all_article_ids)

# bias 한글 변환 함수
def bias_map(bias):
    if bias == 'left':
        return '좌파'
    elif bias == 'right':
        return '우파'
    elif bias == 'center':
        return '중립'
    else:
        return bias
