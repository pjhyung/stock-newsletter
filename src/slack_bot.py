"""
Slack 연동 모듈
- 초안 메시지를 채널에 전송
- ✅ 이모지 감지 + 스레드 코멘트 수집 (폴링 방식)
- Slack 무료 플랜 사용 가능 (봇 기능 무료)
"""
import os
import time
import logging
from datetime import datetime

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

from src.insight_generator import InsightResult

load_dotenv()
logger = logging.getLogger(__name__)

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID", "")

# ✅ 이모지 = 최종 승인 신호
APPROVAL_EMOJI = "white_check_mark"


def format_slack_message(articles: list[dict], insights: InsightResult) -> str:
    """
    Slack mrkdwn 형식의 초안 메시지 구성.
    요약 포인트, 인사이트, 상위 3개 기사 링크, 승인 안내 포함.
    """
    today = datetime.now().strftime("%Y년 %m월 %d일 (%a)")

    # 요약 포인트
    summary_lines = "\n".join([f"• {p}" for p in insights.summary_points])

    # 상위 3개 기사 링크
    top_links = "\n".join([
        f"• <{a['url']}|{a['title']}> — _{a['source']}_"
        for a in articles[:3]
    ])

    return (
        f"📰 *{today} 미국 주식 뉴스레터 초안*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"*📋 오늘의 주요 뉴스 요약*\n"
        f"{summary_lines}\n\n"
        f"*💡 오늘의 투자 인사이트*\n"
        f"{insights.investment_insight}\n\n"
        f"*🔗 주요 기사*\n"
        f"{top_links}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ *승인*: 이 메시지에 ✅ 이모지를 달아주세요.\n"
        f"💬 *수정*: 스레드에 수정 의견을 댓글로 남겨주세요.\n"
        f"_(30분 내 응답이 없으면 현재 초안으로 자동 확정됩니다)_"
    )


def send_draft(message: str, channel: str = "") -> str:
    """
    Slack 채널에 초안 전송.
    반환: 메시지 타임스탬프(ts) — 이후 reactions_get, conversations_replies에 사용.
    """
    ch = channel or SLACK_CHANNEL_ID
    if not ch:
        raise ValueError("SLACK_CHANNEL_ID가 .env에 설정되지 않았습니다.")

    client = WebClient(token=SLACK_BOT_TOKEN)
    response = client.chat_postMessage(
        channel=ch,
        text=message,
        mrkdwn=True,
    )
    ts = response["ts"]
    logger.info(f"Draft sent to Slack channel {ch} (ts={ts})")
    return ts


def wait_for_approval(
    message_ts: str,
    channel: str = "",
    poll_interval: int = 60,
    timeout_minutes: float = 30,
) -> tuple[bool, str]:
    """
    ✅ 이모지가 달릴 때까지 폴링 방식으로 대기.

    반환값:
      (True, user_comment)  → ✅ 이모지 감지됨
      (False, "")           → 타임아웃 (main.py에서 자동 승인 처리)

    user_comment: 스레드의 첫 번째 사용자 댓글 (없으면 빈 문자열)
    """
    ch = channel or SLACK_CHANNEL_ID
    client = WebClient(token=SLACK_BOT_TOKEN)
    deadline = time.time() + (timeout_minutes * 60)

    logger.info(f"Waiting for Slack approval (timeout: {timeout_minutes} min, poll: {poll_interval}s)...")

    while time.time() < deadline:
        try:
            # ── ✅ 이모지 확인 ─────────────────────────────────
            reaction_resp = client.reactions_get(
                channel=ch,
                timestamp=message_ts,
            )
            reactions = reaction_resp["message"].get("reactions", [])
            approved = any(r["name"] == APPROVAL_EMOJI for r in reactions)

            # ── 스레드 댓글 수집 ──────────────────────────────
            thread_resp = client.conversations_replies(
                channel=ch,
                ts=message_ts,
            )
            # messages[0] = 원본 메시지, messages[1:] = 스레드 댓글
            comments = [
                m["text"]
                for m in thread_resp["messages"][1:]
                if not m.get("bot_id")  # 봇 자신의 댓글 제외
            ]
            user_comment = comments[0] if comments else ""

            if approved:
                logger.info(f"✅ Approval received! Comment: '{user_comment or '없음'}'")
                return True, user_comment

            # 댓글 단독으로도 승인 처리 (댓글 자체가 검토 완료 신호)
            if user_comment:
                logger.info(f"💬 Thread comment detected — proceeding: '{user_comment[:60]}'")
                return True, user_comment

            logger.debug(f"No approval yet. Sleeping {poll_interval}s...")

        except SlackApiError as e:
            logger.warning(f"Slack API error during polling: {e.response['error']}")

        time.sleep(poll_interval)

    logger.info("⏰ Approval timeout — auto-approving with current draft.")
    return False, ""


if __name__ == "__main__":
    # 직접 실행 시 연결 테스트
    logging.basicConfig(level=logging.INFO)
    client = WebClient(token=SLACK_BOT_TOKEN)
    auth = client.auth_test()
    print(f"Connected as: {auth['user']} (workspace: {auth['team']})")
