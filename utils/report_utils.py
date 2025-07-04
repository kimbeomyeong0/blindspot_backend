import os
from datetime import datetime

def save_markdown_report(report_clusters, all_article_ids, created_time=None):
    """
    BlindSpot 클러스터 분석 결과를 사람이 보기 좋은 markdown 리포트로 저장
    :param report_clusters: 클러스터별 분석 결과 리스트(dict)
    :param all_article_ids: 전체 기사 ID set
    :param created_time: 생성 시간(datetime, 없으면 now)
    :return: 저장된 파일 경로(str)
    """
    if not report_clusters:
        return None
    os.makedirs('reports', exist_ok=True)
    now = created_time or datetime.now()
    now_str = now.strftime('%Y%m%d_%H%M%S')
    report_path = f'reports/blindspot_analysis_{now_str}.md'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# BlindSpot 언론 편향 분석 리포트\n")
        f.write(f"생성 시간: {now.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"## 📊 전체 요약\n")
        f.write(f"- 🟦 총 클러스터 수: {len(report_clusters)}개\n")
        f.write(f"- 📰 분석된 기사 수: {len(all_article_ids)}개\n\n")
        f.write(f"## 🎯 클러스터별 상세 분석\n\n\n")
        for rc in report_clusters:
            f.write(f"### 🟨 클러스터 {rc['cluster_id']}\n")
            f.write(f"**📝 주제 분석:**\n")
            f.write(f"- 📝 **주제:** {rc['topic']}\n")
            if rc.get('keywords'):
                f.write(f"- 🏷️ **키워드:** {rc['keywords']}\n")
            f.write(f"- 🗂️ **분야:** {rc.get('field', rc.get('category', 'N/A'))}\n\n")
            f.write(f"- 📰 **기사 수:** {rc['article_count']}개\n\n")
            # 언론사별 분포
            f.write(f"**🗞️ 언론사별 분포:**\n")
            for media, count in sorted(rc['media_counter'].items(), key=lambda x: -x[1]):
                bias = rc['media_bias_map'].get(media, '')
                bias_emoji = '🔴' if bias == 'left' else ('🔵' if bias == 'right' else ('⚪' if bias == 'center' else ''))
                f.write(f"- {bias_emoji} {media}: {count}개 ({bias if bias else 'N/A'})\n")
            f.write(f"\n")
            # 편향 분석
            f.write(f"**📈 편향 분석:**\n")
            for bias, (cnt, pct) in rc['bias_pct'].items():
                bias_emoji = '🔴' if bias == 'left' else ('🔵' if bias == 'right' else ('⚪' if bias == 'center' else ''))
                f.write(f"- {bias_emoji} {bias}: {cnt}개 ({pct:.1f}%)\n")
            f.write(f"- 판정: {rc['bias_judgement']}\n\n")
            # 기사 ID
            f.write(f"**🆔 기사 ID:** {', '.join(map(str, rc['article_ids']))}\n\n")
            f.write(f"---\n\n")
    print(f"✅ 리포트 저장 완료: {report_path}")
    return report_path 