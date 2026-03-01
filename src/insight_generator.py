"""
AI 인사이트 생성 모듈 (100% 무료)
- 모델: Gemini 2.0 Flash (google-generativeai)
- 무료 한도: 15 RPM / 1,500 req/day / 1M tokens/day
- 유료 API 없음.
"""
import os
import logging
from dataclasses import dataclass, field

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL_NAME = "gemini-flash-lite-latest"


@dataclass
class InsightResult:
    summary_points: list[str] = field(default_factory=list)
    investment_insight: str = ""
    raw_response: str = ""


def build_prompt(articles: list[dict]) -> str:
    """
    수집된 기사 목록으로 Gemini에 보낼 프롬프트 작성.
    토큰 절약을 위해 최대 20개 기사, 요약은 300자로 자름.
    """
    articles_text = "\n\n".join([
        f"[{i+1}] 출처: {a['source']}\n"
        f"제목: {a['title']}\n"
        f"내용: {a['summary'][:300]}"
        for i, a in enumerate(articles[:20])
    ])

    return f"""당신은 월가 출신 전문 주식 시장 분석가입니다.
아래는 오늘 미국 주식 시장 개장 전 수집된 최신 뉴스입니다.

=== 수집 뉴스 ===
{articles_text}

=== 작성 요청 ===
위 뉴스를 바탕으로 아래 두 섹션을 한국어로 작성해주세요.

SUMMARY:
- 오늘 가장 중요한 뉴스 3~5개를 각각 한 줄로 요약
- 형식: "• [핵심 사실] → [예상 시장 영향]"
- 번호 없이 • 기호로 시작

INSIGHTS:
- '오늘의 투자 인사이트'를 3~4문장으로 작성
- 거시경제(금리·달러·유가)와 개별 섹터(AI·반도체·방산) 관점 균형
- 구체적 티커(NVDA, AAPL 등) 또는 섹터 언급 필수
- 단정적 투자 권유 금지, 분석 관점으로 작성
- 마지막 줄은 반드시 아래 형식의 한 줄 섹터 코멘트로 끝낼 것:
  📌 주목 섹터: [섹터1], [섹터2], [섹터3] — [각 섹터를 주목하는 한 줄 이유]

SUMMARY: 와 INSIGHTS: 헤더를 반드시 포함해주세요."""


def _parse_response(raw: str) -> InsightResult:
    """
    Gemini 응답 텍스트에서 SUMMARY/INSIGHTS 섹션을 파싱.
    헤더 기준으로 분리하고 • 기호로 시작하는 줄을 summary_points로 추출.
    """
    summary_points: list[str] = []
    insight_lines: list[str] = []
    in_summary = False
    in_insight = False

    for line in raw.splitlines():
        stripped = line.strip()
        # "## SUMMARY:" 처럼 마크다운 헤더(#)가 붙어 올 수 있으므로 제거 후 비교
        normalized = stripped.lstrip("#").strip()

        if normalized.upper().startswith("SUMMARY:"):
            in_summary = True
            in_insight = False
            continue
        elif normalized.upper().startswith("INSIGHTS:"):
            in_summary = False
            in_insight = True
            continue

        if in_summary and stripped:
            # "• ..." 또는 "- ..." 또는 "* ..." 또는 숫자 목록 모두 처리
            cleaned = stripped.lstrip("•-–*0123456789.) ").strip()
            cleaned = cleaned.replace("**", "").strip()  # 마크다운 볼드 제거
            if cleaned:
                summary_points.append(cleaned)

        elif in_insight and stripped:
            insight_lines.append(stripped)

    investment_insight = " ".join(insight_lines)

    return InsightResult(
        summary_points=summary_points,
        investment_insight=investment_insight,
        raw_response=raw,
    )


def generate_insights(articles: list[dict]) -> InsightResult:
    """
    기사 리스트를 Gemini 1.5 Flash에 전달하여 InsightResult 반환.
    API 오류 또는 빈 기사 시 fallback InsightResult 반환 (파이프라인 중단 없음).
    """
    if not articles:
        logger.warning("No articles provided to insight generator.")
        return InsightResult(
            summary_points=["수집된 뉴스가 없습니다."],
            investment_insight="오늘은 수집된 뉴스가 없어 인사이트를 생성할 수 없습니다. RSS 피드 상태를 확인해주세요.",
        )

    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is not set in .env")
        return InsightResult(
            summary_points=["GEMINI_API_KEY가 설정되지 않았습니다."],
            investment_insight="[설정 오류] .env 파일에 GEMINI_API_KEY를 입력해주세요. (https://aistudio.google.com/app/apikey)",
        )

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(MODEL_NAME)

        prompt = build_prompt(articles)
        logger.info(f"Sending {len(articles)} articles to Gemini ({MODEL_NAME})...")

        response = model.generate_content(prompt)
        raw_text = response.text
        logger.info(f"Gemini response received ({len(raw_text)} chars)")

        result = _parse_response(raw_text)
        logger.info(f"Parsed {len(result.summary_points)} summary points")
        return result

    except Exception as e:
        logger.error(f"Gemini API call failed: {e}")
        return InsightResult(
            summary_points=[f"AI 분석 중 오류 발생: {str(e)[:120]}"],
            investment_insight="[오류] Gemini API 호출에 실패했습니다. API 키와 네트워크 상태를 확인해주세요.",
        )


if __name__ == "__main__":
    # 직접 실행 시 테스트 (더미 기사)
    logging.basicConfig(level=logging.INFO)
    dummy = [
        {"title": "Fed holds rates steady", "summary": "Federal Reserve keeps rates at 5.25%", "source": "Reuters"},
        {"title": "NVIDIA beats Q4 estimates", "summary": "NVDA reports record data center revenue", "source": "CNBC"},
    ]
    result = generate_insights(dummy)
    print("\n=== Summary Points ===")
    for p in result.summary_points:
        print(f"  • {p}")
    print(f"\n=== Investment Insight ===\n{result.investment_insight}")
