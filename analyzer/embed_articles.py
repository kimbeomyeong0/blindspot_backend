import openai
import numpy as np
import os

def get_embeddings(openai_client, texts, model=None):
    """OpenAI Embeddings API로 텍스트 벡터화"""
    if model is None:
        model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-ada-002")
    try:
        # 텍스트가 너무 길면 자르기 (토큰 제한)
        processed_texts = []
        for text in texts:
            # 제목과 본문 앞부분만 사용 (약 8000자 제한)
            truncated = text[:8000] if len(text) > 8000 else text
            processed_texts.append(truncated)
        
        print(f"🔄 {len(processed_texts)}개 텍스트의 임베딩 생성 중...")
        
        response = openai_client.embeddings.create(
            input=processed_texts,
            model=model,
        )
        
        embeddings = [data.embedding for data in response.data]
        print(f"✅ 임베딩 생성 완료: {len(embeddings)}개")
        
        return np.array(embeddings)
        
    except Exception as e:
        print(f"❌ 임베딩 생성 실패: {e}")
        return None

def prepare_article_texts(articles):
    """기사 텍스트 준비 (제목 + 본문 앞부분)"""
    texts = []
    for article in articles:
        title = article.get('title', '')
        content = article.get('content', '')
        # 제목과 본문 앞 500자를 합쳐서 사용
        combined_text = f"{title}\n\n{content[:500]}"
        texts.append(combined_text)
    return texts 