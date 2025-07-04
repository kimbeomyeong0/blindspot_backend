from sklearn.cluster import KMeans
from .embed_articles import get_embeddings, prepare_article_texts

def find_optimal_clusters(embeddings, max_clusters=10):
    """간단한 방법으로 최적 클러스터 수 찾기"""
    from sklearn.metrics import silhouette_score
    
    inertias = []
    K_range = range(2, min(max_clusters + 1, len(embeddings) // 3 + 1))
    
    for k in K_range:
        kmeans = KMeans(n_clusters=k, random_state=42)
        kmeans.fit(embeddings)
        inertias.append(kmeans.inertia_)
    
    # 간단한 Elbow Method: 기울기 변화가 가장 큰 지점 찾기
    optimal_k = 3  # 기본값
    if len(inertias) > 3:
        # 기울기 변화 계산
        slope_changes = []
        for i in range(1, len(inertias) - 1):
            change = (inertias[i-1] - inertias[i]) - (inertias[i] - inertias[i+1])
            slope_changes.append(change)
        
        if slope_changes:
            optimal_k = K_range[slope_changes.index(max(slope_changes)) + 1]
    
    print(f"🎯 자동 계산된 최적 클러스터 수: {optimal_k}개")
    return optimal_k

def cluster_articles(openai_client, articles, n_clusters=None):
    """기사들을 주제별로 클러스터링"""
    print(f"\n🎯 {len(articles)}개 기사 클러스터링 시작...")
    
    # 기사 텍스트 준비
    texts = prepare_article_texts(articles)
    
    # OpenAI 임베딩 생성
    embeddings = get_embeddings(openai_client, texts)
    if embeddings is None:
        return None
    
    # 최적 클러스터 수 결정
    if n_clusters is None:
        n_clusters = find_optimal_clusters(embeddings)
    else:
        print(f"🎯 사용자 지정 클러스터 수: {n_clusters}개")
    
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