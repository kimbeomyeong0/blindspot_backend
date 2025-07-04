#!/usr/bin/env python3
"""
BlindSpot 전체 파이프라인 실행 스크립트

실행 순서:
1. 📰 기사 크롤링 (병렬 처리)
2. 🧠 기사 분석 (임베딩 → 클러스터링 → 요약)
3. 📊 결과 리포트 생성
"""

import os
import sys
import time
from datetime import datetime
import openai
from dotenv import load_dotenv
from collections import Counter, defaultdict

# .env 파일 로드
load_dotenv()

# 모듈 import
from main_crawler import crawl_all_parallel
from supabase_utils import init_supabase, load_articles_from_db, save_cluster_to_db, save_cluster_articles_to_db, save_analysis_session_to_db
from analyzer import cluster_articles, analyze_cluster_topics, analyze_media_bias, generate_report
from report_utils import save_markdown_report

class BlindSpotPipeline:
    def __init__(self, openai_api_key):
        """파이프라인 초기화"""
        self.openai_client = openai.OpenAI(api_key=openai_api_key)
        self.supabase = init_supabase()
        print("🤖 BlindSpot 파이프라인 초기화 완료")
    
    def calculate_optimal_clusters(self, article_count):
        """기사 수에 따라 최적 클러스터 수 계산 (최대 15개 제한)"""
        if article_count < 30:
            return 3
        elif article_count < 60:
            return 5
        elif article_count < 120:
            return 8
        elif article_count < 200:
            return 10
        else:
            return min(15, max(8, article_count // 25))  # 기사 25개당 1개 클러스터, 최대 15개 제한
        
    def step1_crawl_articles(self):
        """1단계: 기사 크롤링"""
        print("\n" + "="*60)
        print("📰 1단계: 기사 크롤링 시작")
        print("="*60)
        
        start_time = time.time()
        articles = crawl_all_parallel()
        end_time = time.time()
        
        print(f"✅ 크롤링 완료! 소요시간: {end_time - start_time:.1f}초")
        print(f"📊 수집된 기사: {len(articles)}개")
        
        return articles
    
    def step2_analyze_articles(self, n_clusters=None):
        """2단계: 기사 분석 (카테고리별 클러스터링)"""
        print("\n" + "="*60)
        print("🧠 2단계: 기사 분석 시작 (카테고리별)")
        print("="*60)
        
        # DB에서 기사 로드
        print("📊 DB에서 기사 데이터 로드 중...")
        articles = load_articles_from_db(self.supabase)
        
        if not articles:
            print("❌ 분석할 기사가 없습니다.")
            return None
        
        print(f"📊 총 {len(articles)}개 기사 로드 완료")
        
        # 카테고리별로 기사 분리
        articles_by_category = {}
        for article in articles:
            category = None
            if 'categories' in article and isinstance(article['categories'], dict):
                category = article['categories'].get('name')
            elif 'category' in article:
                category = article['category']
            if category:
                articles_by_category.setdefault(category, []).append(article)

        all_results = []
        report_clusters = []
        all_article_ids = set()
        for category, articles_in_cat in articles_by_category.items():
            if not articles_in_cat:
                continue
            print(f"\n[{category}] 기사 {len(articles_in_cat)}개 클러스터링 시작!")
            n_cat_clusters = self.calculate_optimal_clusters(len(articles_in_cat)) if n_clusters is None else n_clusters
            print(f"[DEBUG] {category} n_clusters: {n_cat_clusters}")
            result = cluster_articles(self.openai_client, articles_in_cat, n_cat_clusters)
            if result is None:
                print(f"{category} 클러스터링 실패")
                continue
            clustered_articles, cluster_centers = result
            print(f"[DEBUG] {category} 클러스터 개수: {n_cat_clusters}, 실제 클러스터링된 기사 수: {len(clustered_articles)}")
            cluster_topics = analyze_cluster_topics(self.openai_client, clustered_articles)
            bias_analysis = analyze_media_bias(cluster_topics)
            report = generate_report(bias_analysis)
            all_results.append({
                'category': category,
                'clustered_articles': clustered_articles,
                'cluster_topics': cluster_topics,
                'bias_analysis': bias_analysis,
                'report': report
            })
            self.save_analysis_results_to_db(clustered_articles, cluster_topics, bias_analysis, category)
            # 리포트용 데이터 누적 (run_cluster_save.py와 동일하게)
            for cluster_id, articles_in_cluster in enumerate(clustered_articles):
                cluster_info = cluster_topics.get(cluster_id, {})
                if not cluster_info.get('summary'):
                    continue
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
                total = sum(bias_counter.values())
                bias_pct = {k: (v, v/total*100 if total else 0) for k, v in bias_counter.items()}
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
                topic = cluster_info.get('topic_analysis', f'클러스터 {cluster_id}')
                summary = cluster_info.get('summary', '')
                keywords = cluster_info.get('keywords', None)
                field = cluster_info.get('분야', None) or cluster_info.get('field', None) or category
                if isinstance(articles_in_cluster, dict):
                    article_ids = [articles_in_cluster.get('id')] if articles_in_cluster.get('id') else []
                elif isinstance(articles_in_cluster, list) and articles_in_cluster and isinstance(articles_in_cluster[0], dict):
                    article_ids = [a.get('id') for a in articles_in_cluster if a.get('id')]
                elif isinstance(articles_in_cluster, list):
                    article_ids = [a for a in articles_in_cluster if a]
                else:
                    article_ids = []
                all_article_ids.update(article_ids)
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
        if report_clusters:
            save_markdown_report(report_clusters, all_article_ids)
        return all_results
    
    def save_analysis_results_to_db(self, clustered_articles, cluster_topics, bias_analysis, category=None):
        """분석 결과를 데이터베이스에 저장 (카테고리 포함)"""
        try:
            print("📊 클러스터 정보 저장 중...")
            # 클러스터별 기사 리스트로 변환
            clusters_dict = {}
            for article in clustered_articles:
                cid = article['cluster_id']
                if cid not in clusters_dict:
                    clusters_dict[cid] = []
                clusters_dict[cid].append(article)
            for cluster_id, articles_in_cluster in clusters_dict.items():
                cluster_info = cluster_topics.get(cluster_id, {})
                # summary만 체크
                if not cluster_info.get('summary'):
                    print(f"❌ 파싱 실패: cluster_id={cluster_id}, summary='{cluster_info.get('summary')}'")
                    continue
                cluster_data = {
                    'cluster_id': cluster_id,
                    'category': category,
                    'topic': cluster_info.get('topic', f'클러스터 {cluster_id}'),
                    'summary': cluster_info.get('summary', ''),
                    'article_count': len(articles_in_cluster)
                }
                print("저장 시도:", cluster_data)
                print(f"클러스터 {cluster_id} 예시:", articles_in_cluster[:1])
                print("타입:", type(articles_in_cluster))
                save_cluster_to_db(self.supabase, cluster_data)

                # 기사 ID 저장
                article_ids = [a.get('id') for a in articles_in_cluster if a.get('id')]
                if article_ids:
                    save_cluster_articles_to_db(self.supabase, cluster_id, article_ids)
            print(f"✅ [{category}] 클러스터 DB 저장 완료!")
            return True
        except Exception as e:
            print(f"❌ 분석 결과 DB 저장 실패: {e}")
            return False
    
    def save_report(self, report):
        """분석 리포트 저장"""
        # reports 폴더가 없으면 생성
        reports_dir = "reports"
        if not os.path.exists(reports_dir):
            os.makedirs(reports_dir)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_filename = os.path.join(reports_dir, f"blindspot_analysis_{timestamp}.md")
        
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"✅ 리포트 저장 완료: {report_filename}")
        return report_filename
    
    def run_full_pipeline(self, n_clusters=None):
        """전체 파이프라인 실행"""
        print("🚀 BlindSpot 전체 파이프라인 시작!")
        print(f"⏰ 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        total_start_time = time.time()
        
        try:
            # 1단계: 크롤링
            articles = self.step1_crawl_articles()
            
            # 2단계: 분석
            analysis_results = self.step2_analyze_articles(n_clusters)
            
            if analysis_results:
                # 리포트 저장
                report_filename = self.save_report(analysis_results[0]['report'])
                
                total_end_time = time.time()
                total_duration = total_end_time - total_start_time
                
                print("\n" + "="*60)
                print("🎉 BlindSpot 파이프라인 완료!")
                print("="*60)
                print(f"⏰ 종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"⏱️ 총 소요 시간: {total_duration:.1f}초")
                print(f"📊 수집된 기사: {len(articles)}개")
                print(f"📋 분석 리포트: {report_filename}")
                
                # 리포트 내용 출력
                print("\n" + "="*60)
                print("📋 분석 결과 미리보기")
                print("="*60)
                print(analysis_results[0]['report'][:1000] + "...")
                
                return {
                    'success': True,
                    'articles_count': len(articles),
                    'report_filename': report_filename,
                    'total_duration': total_duration
                }
            else:
                print("❌ 분석 단계에서 실패했습니다.")
                return {'success': False, 'error': '분석 실패'}
                
        except Exception as e:
            print(f"❌ 파이프라인 실행 중 오류: {e}")
            return {'success': False, 'error': str(e)}

def main():
    """메인 실행 함수"""
    print("🔑 BlindSpot 파이프라인")
    print("="*40)
    
    # OpenAI API 키 환경변수에서 가져오기
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("❌ OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        print("💡 .env 파일에 OPENAI_API_KEY를 추가해주세요.")
        return
    
    # 클러스터 수는 무조건 자동 계산
    n_clusters = None
    
    # OpenAI 모델명은 환경변수에서 불러오기
    openai_model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    
    # 파이프라인 실행
    pipeline = BlindSpotPipeline(api_key)
    result = pipeline.run_full_pipeline(n_clusters)
    
    if result['success']:
        print(f"\n🎉 성공적으로 완료되었습니다!")
        print(f"📊 수집된 기사: {result['articles_count']}개")
        print(f"📋 리포트 파일: {result['report_filename']}")
        print(f"⏱️ 총 소요 시간: {result['total_duration']:.1f}초")
    else:
        print(f"\n❌ 실패했습니다: {result.get('error', '알 수 없는 오류')}")

if __name__ == "__main__":
    main() 