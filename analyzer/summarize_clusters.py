from datetime import datetime
import re
import os

def analyze_cluster_topics(openai_client, clustered_articles):
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
        
        # GPT에게 주제 분석 및 summary 요청
        prompt = f"""
다음은 뉴스 기사 제목들입니다. 이 기사들의 공통 주제를 분석하고, 전체 내용을 한 문장으로 요약(summary)도 작성해주세요.

기사 제목들:
{titles_text}

응답 형식:
1. 주제: (한 문장으로 요약)
2. 키워드: (3-5개)
3. 분야: (정치/경제/사회/국제/문화 등)
4. summary: (전체 내용을 한 문장으로 요약)
"""
        
        try:
            response = openai_client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.3
            )
            analysis = response.choices[0].message.content
            print(f"\n[GPT 응답] analysis:\n{analysis}\n")  # 실제 GPT 응답 전체 출력
            
            # summary 파싱 - 더 유연한 패턴
            summary = ""
            summary_patterns = [
                r"4\\. summary:\s*([\s\S]+)$",  # 4. summary: 이후 ~ 끝까지
                r"summary:\s*([\s\S]+)$",        # summary: 이후 ~ 끝까지
                r"4\\. summary:\s*([^\n]+)",    # 4. summary: 한 줄만
                r"summary:\s*([^\n]+)"
            ]
            for pattern in summary_patterns:
                summary_match = re.search(pattern, analysis, re.IGNORECASE)
                if summary_match:
                    summary = summary_match.group(1).strip()
                    print(f"🔍 [디버깅] 유연 파싱 summary: '{summary}'")
                    break
            if not summary:
                print(f"❌ [경고] summary 파싱 실패! 원본 일부: {analysis[:80]}")
            
            cluster_topics[cluster_id] = {
                'topic': analysis,
                'summary': summary,
                'articles': articles
            }
            
            # 디버깅: 최종 cluster_topics[cluster_id] 확인
            print(f"🔍 [디버깅] cluster_topics[{cluster_id}]: {cluster_topics[cluster_id]}")
            
        except Exception as e:
            print(f"❌ 클러스터 {cluster_id} 분석 실패: {e}")
            cluster_topics[cluster_id] = {
                'topic': "분석 실패",
                'summary': "",
                'articles': articles
            }
    
    # 디버깅: 최종 반환값 확인
    print(f"🔍 [디버깅] 최종 cluster_topics 반환값:")
    for cluster_id, data in cluster_topics.items():
        print(f"  - cluster_id {cluster_id}: summary='{data.get('summary', '')}'")
    
    return cluster_topics

def analyze_media_bias(cluster_topics):
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
            'topic': cluster_data['topic'],
            'total_articles': len(articles),
            'media_breakdown': media_count,
            'bias_summary': bias_summary
        }
    
    return bias_analysis

def generate_report(bias_analysis):
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