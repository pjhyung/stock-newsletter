"""
HTML 뉴스레터 생성 모듈
Jinja2로 template.html을 렌더링하여 output/newsletter_YYYYMMDD.html로 저장.
"""
import os
import logging
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from dotenv import load_dotenv

from src.insight_generator import InsightResult

load_dotenv()
logger = logging.getLogger(__name__)

# templates/ 디렉토리는 src/ 의 부모(= 프로젝트 루트) 기준
TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
DEFAULT_OUTPUT_DIR = Path(__file__).parent.parent / "output"
NEWSLETTER_AUTHOR = os.getenv("NEWSLETTER_AUTHOR", "편집자")


def build_newsletter_html(
    articles: list[dict],
    insights: InsightResult,
    user_comment: str = "",
) -> str:
    """
    Jinja2 템플릿에 데이터를 주입하여 완성된 HTML 문자열을 반환.
    articles는 최대 10개만 렌더링 (HTML 길이 제한).
    """
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("template.html")

    context = {
        "date": datetime.now().strftime("%Y년 %m월 %d일"),
        "summary_points": insights.summary_points,
        "investment_insight": insights.investment_insight,
        "articles": articles[:10],
        "user_comment": user_comment,
        "author": NEWSLETTER_AUTHOR,
    }

    html = template.render(**context)
    logger.info(f"HTML rendered ({len(html):,} chars)")
    return html


def save_newsletter(html: str, output_dir: str = "") -> str:
    """
    렌더링된 HTML을 output/newsletter_YYYYMMDD.html로 저장.
    저장 경로(str)를 반환.
    같은 날 재실행 시 덮어씀.
    """
    out_dir = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    filename = f"newsletter_{datetime.now().strftime('%Y%m%d')}.html"
    filepath = out_dir / filename

    filepath.write_text(html, encoding="utf-8")
    logger.info(f"Newsletter saved → {filepath}")
    return str(filepath)


if __name__ == "__main__":
    # 직접 실행 시 더미 데이터로 렌더링 테스트
    logging.basicConfig(level=logging.INFO)

    dummy_articles = [
        {
            "title": "NVIDIA Posts Record Revenue Driven by AI Chip Demand",
            "url": "https://example.com/nvda",
            "summary": "NVIDIA reported record quarterly revenue of $22.1 billion.",
            "source": "Reuters",
            "published": "2026-03-01",
        },
        {
            "title": "Fed Signals Potential Rate Cuts Later This Year",
            "url": "https://example.com/fed",
            "summary": "Federal Reserve officials indicated possible rate reductions.",
            "source": "CNBC",
            "published": "2026-03-01",
        },
    ]
    dummy_insights = InsightResult(
        summary_points=[
            "NVIDIA 분기 매출 사상 최대 → AI 인프라 투자 사이클 가속화 신호",
            "연준 금리 인하 시사 → 성장주·기술주에 긍정적",
        ],
        investment_insight=(
            "오늘 시장의 핵심은 AI 인프라 수요의 지속성과 통화정책 완화 기대감의 교차입니다. "
            "NVDA를 중심으로 한 반도체 섹터는 강세가 예상되며, "
            "금리 민감도가 높은 성장주(AMZN, MSFT)도 수혜가 기대됩니다."
        ),
    )

    html = build_newsletter_html(dummy_articles, dummy_insights, user_comment="좋은 분석입니다!")
    path = save_newsletter(html)
    print(f"Test newsletter saved: {path}")
