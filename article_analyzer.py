import openai
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
import json
from datetime import datetime
import sys
import os

# supabase_client import
from supabase_client import init_supabase

class BlindSpotAnalyzer:
    def __init__(self, openai_api_key):
        """BlindSpot 기사 분석기 초기화"""
        self.openai_client = openai.OpenAI(api_key=openai_api_key)
        self.supabase = init_supabase()
        print("🤖 OpenAI 클라이언트 및 Supabase 연결 완료")
        
    def load_articles_from_db(self):
        """Supabase에서 모든 기사 데이터 로드"""
        try:
            # 기사와 언론사, 카테고리 정보를 JOIN해서 가져오기
            response = self.supabase.table('articles').select("""
                id,
                title,
                content,
                url,
                published_at,
                media_outlets(name, bias),
                categories(name)
            """).execute()
            
            print(f"📊 총 {len(response.data)}개 기사 로드 완료")
            return response.data
            
        except Exception as e:
            print(f"❌ 기사 로드 실패: {e}")
            return []
    
    def get_embeddings(self, texts, model="text-embedding-ada-002"):
        """OpenAI Embeddings API로 텍스트 벡터화"""
        try:
            # 텍스트가 너무 길면 자르기 (토큰 제한)
            processed_texts = []
            for text in texts:
                # 제목과 본문 앞부분만 사용 (약 8000자 제한)
                truncated = text[:8000] if len(text) > 8000 else text
                processed_texts.append(truncated)
            
            print(f"🔄 {len(processed_texts)}개 텍스트의 임베딩 생성 중...")
            
            response = self.openai_client.embeddings.create(
                model=model,
                input=processed_texts
            )
            
            embeddings = [data.embedding for data in response.data]
            print(f"✅ 임베딩 생성 완료: {len(embeddings)}개")
            
            return np.array(embeddings)
            
        except Exception as e:
            print(f"❌ 임베딩 생성 실패: {e}")
            return None
    
    def cluster_articles(self, articles, n_clusters=8):
        """기사들을 주제별로 클러스터링"""
        print(f"\n🎯 {len(articles)}개 기사를 {n_clusters}개 클러스터로 분류 중...")
        
        # 기사 텍스트 준비 (제목 + 본문 앞부분)
        texts = []
        for article in articles:
            title = article.get('title', '')
            content = article.get('content', '')
            # 제목과 본문 앞 500자를 합쳐서 사용
            combined_text = f"{title}\n\n{content[:500]}"
            texts.append(combined_text)
        
        # OpenAI 임베딩 생성
        embeddings = self.get_embeddings(texts)
        if embeddings is None:
            return None
        
        # K-means 클러스터링
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        cluster_labels = kmeans.fit_predict(embeddings)
        
        # 결과 정리
        clustered_articles = []
        for i, article in enumerate(articles):
            article_with_cluster = article.copy()
            article_with_cluster['cluster_id'] = int(cluster_labels[i])
            article_with_cluster['embedding'] = embeddings[i].tolist()
            clustered_articles.append(article_with_cluster)
        
        print(f"✅ 클러스터링 완료!")
        return clustered_articles, kmeans.cluster_centers_
    
    def analyze_cluster_topics(self, clustered_articles):
        """GPT를 사용해서 각 클러스터의 주제 분석"""
        print(f"\n📝 클러스터별 주제 분석 중...")
        
        # 클러스터별로 기사 그룹화
        clusters = {}
        for article in clustered_articles:
            cluster_id = article['cluster_id']
            if cluster_id not in clusters:
                clusters[cluster_id] = []
            clusters[cluster_id].append(article)
        
        cluster_topics = {}
        
        for cluster_id, articles in clusters.items():
            print(f"클러스터 {cluster_id} 분석 중... ({len(articles)}개 기사)")
            
            # 클러스터의 대표 기사 제목들
            titles = [article['title'] for article in articles[:10]]  # 상위 10개만
            titles_text = "\n".join([f"- {title}" for title in titles])
            
            # GPT에게 주제 분석 요청
            prompt = f"""
다음은 뉴스 기사 제목들입니다. 이 기사들의 공통 주제를 분석해주세요.

기사 제목들:
{titles_text}

응답 형식:
1. 주제: (한 문장으로 요약)
2. 키워드: (3-5개)
3. 분야: (정치/경제/사회/국제/문화 등)
"""
            
            try:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=200,
                    temperature=0.3
                )
                
                analysis = response.choices[0].message.content
                cluster_topics[cluster_id] = {
                    'topic_analysis': analysis,
                    'article_count': len(articles),
                    'articles': articles
                }
                
            except Exception as e:
                print(f"❌ 클러스터 {cluster_id} 분석 실패: {e}")
                cluster_topics[cluster_id] = {
                    'topic_analysis': "분석 실패",
                    'article_count': len(articles),
                    'articles': articles
                }
        
        return cluster_topics
    
    def analyze_media_bias(self, cluster_topics):
        """클러스터별 언론사 편향 분석"""
        print(f"\n⚖️ 언론사별 편향 분석 중...")
        
        bias_analysis = {}
        
        for cluster_id, cluster_data in cluster_topics.items():
            articles = cluster_data['articles']
            
            # 언론사별 기사 수 집계
            media_count = {}
            for article in articles:
                media_name = article['media_outlets']['name']
                media_bias = article['media_outlets']['bias']
                
                if media_name not in media_count:
                    media_count[media_name] = {
                        'count': 0,
                        'bias': media_bias,
                        'titles': []
                    }
                media_count[media_name]['count'] += 1
                media_count[media_name]['titles'].append(article['title'])
            
            # 편향별 집계
            bias_summary = {'left': 0, 'center': 0, 'right': 0}
            for media, data in media_count.items():
                bias_summary[data['bias']] += data['count']
            
            bias_analysis[cluster_id] = {
                'topic': cluster_data['topic_analysis'],
                'total_articles': len(articles),
                'media_breakdown': media_count,
                'bias_summary': bias_summary
            }
        
        return bias_analysis
    
    def generate_report(self, bias_analysis):
        """분석 결과 리포트 생성"""
        print(f"\n📋 BlindSpot 분석 리포트 생성 중...")
        
        report = f"""
# BlindSpot 언론 편향 분석 리포트
생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📊 전체 요약
- 총 클러스터 수: {len(bias_analysis)}개
- 분석된 기사 수: {sum(data['total_articles'] for data in bias_analysis.values())}개

## 🎯 클러스터별 상세 분석

"""
        
        for cluster_id, data in bias_analysis.items():
            report += f"""
### 클러스터 {cluster_id}
**주제 분석:**
{data['topic'].replace('1. ', '**주제:** ').replace('2. ', '**키워드:** ').replace('3. ', '**분야:** ')}

**기사 수:** {data['total_articles']}개

**언론사별 분포:**
"""
            for media, media_data in data['media_breakdown'].items():
                bias_emoji = {'left': '🔴', 'center': '⚪', 'right': '🔵'}[media_data['bias']]
                report += f"- {bias_emoji} {media}: {media_data['count']}개 ({media_data['bias']})\n"
            
            left = data['bias_summary']['left']
            center = data['bias_summary']['center'] 
            right = data['bias_summary']['right']
            total = left + center + right
            
            if total > 0:
                report += f"""
**편향 분석:**
- 🔴 좌파 성향: {left}개 ({left/total*100:.1f}%)
- ⚪ 중립 성향: {center}개 ({center/total*100:.1f}%)
- 🔵 우파 성향: {right}개 ({right/total*100:.1f}%)

**편향 판정:** """
                
                if left > right + center:
                    report += "🔴 좌편향 우세"
                elif right > left + center:
                    report += "🔵 우편향 우세"
                elif center > left + right:
                    report += "⚪ 중립 우세"
                else:
                    report += "⚖️ 균형적 보도"
            
            report += "\n---\n"
        
        return report
    
    def run_full_analysis(self, n_clusters=8):
        """전체 분석 프로세스 실행"""
        print("🚀 BlindSpot 언론 편향 분석 시작!")
        print("=" * 60)
        
        # 1. 기사 데이터 로드
        articles = self.load_articles_from_db()
        if not articles:
            print("❌ 분석할 기사가 없습니다.")
            return None
        
        # 2. 클러스터링
        result = self.cluster_articles(articles, n_clusters)
        if result is None:
            print("❌ 클러스터링 실패")
            return None
        
        clustered_articles, cluster_centers = result
        
        # 3. 클러스터 주제 분석
        cluster_topics = self.analyze_cluster_topics(clustered_articles)
        
        # 4. 편향 분석
        bias_analysis = self.analyze_media_bias(cluster_topics)
        
        # 5. 리포트 생성
        report = self.generate_report(bias_analysis)
        
        # 6. 결과 저장
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_filename = f"blindspot_analysis_{timestamp}.md"
        
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"✅ 분석 완료! 리포트 저장: {report_filename}")
        print("\n" + "=" * 60)
        print(report)
        
        return {
            'clustered_articles': clustered_articles,
            'cluster_topics': cluster_topics,
            'bias_analysis': bias_analysis,
            'report': report
        }

# 실행용 함수
def main():
    # OpenAI API 키 입력 받기
    api_key = input("🔑 OpenAI API 키를 입력하세요: ").strip()
    
    if not api_key:
        print("❌ API 키가 필요합니다.")
        return
    
    # 분석 실행
    analyzer = BlindSpotAnalyzer(api_key)
    result = analyzer.run_full_analysis(n_clusters=6)  # 6개 클러스터로 시작
    
    if result:
        print("🎉 BlindSpot 분석이 완료되었습니다!")

if __name__ == "__main__":
    main()