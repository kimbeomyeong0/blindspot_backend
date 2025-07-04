"""
클러스터별 편향성 분석 및 점수 계산 모듈
"""
from collections import Counter
from typing import List, Dict, Any

def get_bias_score(bias_type: str) -> float:
    """편향성 타입을 숫자 점수로 변환
    
    Args:
        bias_type (str): 'left', 'center', 'right' 중 하나
        
    Returns:
        float: 편향성 점수 (-1.0 ~ +1.0)
    """
    bias_scores = {
        'left': -1.0,    # 좌편향
        'center': 0.0,   # 중도
        'right': 1.0     # 우편향
    }
    return bias_scores.get(bias_type.lower(), 0.0)

def calculate_cluster_bias_percentage(cluster_articles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """클러스터 내 기사들의 편향성 비율 계산 (프론트엔드용)
    
    Args:
        cluster_articles: 클러스터에 속한 기사들 리스트
        
    Returns:
        dict: 편향성 분석 결과
        {
            'bias': {'left': 40, 'center': 35, 'right': 25},  # 비율 (%)
            'media_distribution': dict,  # 언론사별 기사 수
            'total_articles': int,       # 총 기사 수
            'bias_score': float         # 전체 편향성 점수 (-1.0 ~ +1.0)
        }
    """
    if not cluster_articles:
        return {
            'bias': {'left': 0, 'center': 100, 'right': 0},
            'media_distribution': {},
            'total_articles': 0,
            'bias_score': 0.0
        }
    
    # 언론사별, 편향별 집계
    media_counter = Counter()
    bias_counter = Counter()
    bias_scores = []
    
    for article in cluster_articles:
        # 언론사 정보 추출
        media_info = article.get('media_outlets', {})
        if isinstance(media_info, dict):
            media_name = media_info.get('name', 'Unknown')
            bias_type = media_info.get('bias', 'center')
        else:
            media_name = 'Unknown'
            bias_type = 'center'
        
        # 집계
        media_counter[media_name] += 1
        bias_counter[bias_type] += 1
        
        # 편향성 점수 수집
        score = get_bias_score(bias_type)
        bias_scores.append(score)
    
    # 전체 편향성 점수 계산 (가중평균)
    total_score = sum(bias_scores) / len(bias_scores) if bias_scores else 0.0
    
    # 편향별 개수
    left_count = bias_counter.get('left', 0)
    center_count = bias_counter.get('center', 0)
    right_count = bias_counter.get('right', 0)
    total_count = len(cluster_articles)
    
    # 비율 계산 (소수점 반올림)
    bias_percentage = {
        'left': round((left_count / total_count) * 100) if total_count > 0 else 0,
        'center': round((center_count / total_count) * 100) if total_count > 0 else 100,
        'right': round((right_count / total_count) * 100) if total_count > 0 else 0
    }
    
    # 반올림으로 인한 합계 오차 보정 (100%가 되도록)
    total_percentage = sum(bias_percentage.values())
    if total_percentage != 100 and total_count > 0:
        # 가장 큰 값에 차이를 더하거나 빼서 100으로 맞춤
        max_key = max(bias_percentage.keys(), key=lambda k: bias_percentage[k])
        bias_percentage[max_key] += (100 - total_percentage)
    
    return {
        'bias': bias_percentage,
        'media_distribution': dict(media_counter),
        'total_articles': total_count,
        'bias_score': round(total_score, 3)
    }

def calculate_cluster_bias_score(cluster_articles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """클러스터 내 기사들의 편향성 점수 계산 (기존 함수 - 호환성 유지)
    
    Args:
        cluster_articles: 클러스터에 속한 기사들 리스트
        
    Returns:
        dict: 편향성 분석 결과 (기존 형태)
    """
    result = calculate_cluster_bias_percentage(cluster_articles)
    
    # 기존 형태로 변환
    bias_distribution = {
        'left': int(result['total_articles'] * result['bias']['left'] / 100),
        'center': int(result['total_articles'] * result['bias']['center'] / 100),
        'right': int(result['total_articles'] * result['bias']['right'] / 100)
    }
    
    # 편향성 라벨 결정
    if result['bias_score'] < -0.3:
        bias_label = 'left'
    elif result['bias_score'] > 0.3:
        bias_label = 'right'
    else:
        bias_label = 'center'
    
    return {
        'bias_score': result['bias_score'],
        'media_distribution': result['media_distribution'],
        'bias_distribution': bias_distribution,
        'total_articles': result['total_articles'],
        'bias_label': bias_label,
        'bias_percentage': result['bias']  # 새로운 비율 정보 추가
    }

def calculate_all_clusters_bias(clustered_articles: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    """모든 클러스터의 편향성 비율 계산 (프론트엔드용)
    
    Args:
        clustered_articles: 클러스터링된 모든 기사들
        
    Returns:
        dict: 클러스터 ID별 편향성 분석 결과
    """
    # 클러스터별로 기사 그룹화
    clusters = {}
    for article in clustered_articles:
        cluster_id = article.get('cluster_id')
        if cluster_id is not None:
            if cluster_id not in clusters:
                clusters[cluster_id] = []
            clusters[cluster_id].append(article)
    
    # 각 클러스터별 편향성 계산
    bias_results = {}
    print(f"\n📊 클러스터별 편향성 분석 시작...")
    
    for cluster_id, articles in clusters.items():
        bias_analysis = calculate_cluster_bias_percentage(articles)
        bias_results[cluster_id] = bias_analysis
        
        bias_info = bias_analysis['bias']
        print(f"   클러스터 {cluster_id}: {bias_analysis['total_articles']}개 기사")
        print(f"   편향성 비율: 좌={bias_info['left']}%, 중={bias_info['center']}%, 우={bias_info['right']}%")
        print(f"   편향성 점수: {bias_analysis['bias_score']}")
    
    print(f"✅ 총 {len(bias_results)}개 클러스터 편향성 분석 완료!")
    return bias_results

def get_bias_summary_text(bias_analysis: Dict[str, Any]) -> str:
    """편향성 분석 결과를 텍스트로 요약
    
    Args:
        bias_analysis: calculate_cluster_bias_score 결과
        
    Returns:
        str: 요약 텍스트
    """
    score = bias_analysis['bias_score']
    label = bias_analysis['bias_label']
    distribution = bias_analysis['bias_distribution']
    
    # 편향성 강도 계산
    abs_score = abs(score)
    if abs_score < 0.2:
        intensity = "약간"
    elif abs_score < 0.5:
        intensity = "보통"
    elif abs_score < 0.8:
        intensity = "강한"
    else:
        intensity = "매우 강한"
    
    # 라벨별 텍스트
    label_text = {
        'left': f"{intensity} 좌편향",
        'right': f"{intensity} 우편향", 
        'center': "중도"
    }
    
    # 분포 정보
    total = sum(distribution.values())
    if total > 0:
        dist_text = f"(좌:{distribution['left']}, 중:{distribution['center']}, 우:{distribution['right']})"
    else:
        dist_text = ""
    
    return f"{label_text.get(label, '중도')} {dist_text}" 