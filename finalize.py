"""
기존 Slack 스레드 댓글을 읽어서 HTML 뉴스레터를 즉시 생성하는 스크립트.
Slack 재전송·대기 없이 finalize 단계만 실행.
"""
import io, sys, os, logging
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("finalize")

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from src.news_fetcher import collect_news
from src.insight_generator import generate_insights
from src.html_builder import build_newsletter_html, save_newsletter

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID", "")

# 마지막으로 전송된 Slack 메시지 타임스탬프
LAST_MESSAGE_TS = "1772340851.475029"


def fetch_thread_comment(ts: str) -> str:
    """기존 Slack 메시지 스레드에서 첫 번째 사용자 댓글을 읽어온다."""
    client = WebClient(token=SLACK_BOT_TOKEN)
    try:
        resp = client.conversations_replies(channel=SLACK_CHANNEL_ID, ts=ts)
        comments = [
            m["text"]
            for m in resp["messages"][1:]
            if not m.get("bot_id")
        ]
        if comments:
            logger.info(f"Thread comment found: '{comments[0][:80]}'")
            return comments[0]
        else:
            logger.warning("No thread comment found — generating without comment.")
            return ""
    except SlackApiError as e:
        logger.error(f"Slack error: {e.response['error']}")
        return ""


def main():
    logger.info("=" * 50)
    logger.info("Finalizing newsletter with Slack thread comment")
    logger.info("=" * 50)

    # 1. 스레드 댓글 읽기
    logger.info("[1/4] Reading Slack thread comment...")
    user_comment = fetch_thread_comment(LAST_MESSAGE_TS)

    # 2. 뉴스 재수집
    logger.info("[2/4] Re-collecting news...")
    articles = collect_news(hours_back=12, max_articles=30)
    logger.info(f"  -> {len(articles)} articles")

    # 3. Gemini 인사이트 생성
    logger.info("[3/4] Generating insights...")
    insights = generate_insights(articles)
    logger.info(f"  -> {len(insights.summary_points)} summary points")

    # 4. HTML 생성 + 저장
    logger.info("[4/4] Building HTML newsletter...")
    html = build_newsletter_html(articles, insights, user_comment=user_comment)
    path = save_newsletter(html)

    logger.info("=" * 50)
    logger.info(f"Done! Newsletter saved: {path}")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
