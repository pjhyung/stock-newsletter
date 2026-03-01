"""
미국 주식 뉴스레터 파이프라인 오케스트레이터

사용법:
  python main.py              # 즉시 1회 실행
  python main.py --schedule   # 매일 08:00 KST (= 23:00 UTC)에 자동 실행 (로컬 전용)

GitHub Actions에서는 --schedule 없이 main.py만 실행하면 됨.
"""
import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

# Windows CP949 콘솔에서 이모지/한글 로그 깨짐 방지
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv

# 프로젝트 루트를 sys.path에 추가 (어느 디렉토리에서 실행해도 동작)
sys.path.insert(0, str(Path(__file__).parent))

load_dotenv()

# ── 로깅 설정 ───────────────────────────────────────────────
log_dir = Path(__file__).parent / "output"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"pipeline_{datetime.now().strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(log_file), encoding="utf-8"),
    ],
)
logger = logging.getLogger("main")

# 모듈 import (로깅 설정 후)
from src.news_fetcher import collect_news
from src.insight_generator import generate_insights
from src.slack_bot import format_slack_message, send_draft, wait_for_approval
from src.html_builder import build_newsletter_html, save_newsletter


def run_pipeline() -> None:
    """
    뉴스레터 파이프라인 전체 실행:
    1. 뉴스 수집 (feedparser RSS)
    2. AI 요약 (Gemini 1.5 Flash)
    3. Slack 초안 전송
    4. 승인/코멘트 대기
    5. HTML 뉴스레터 생성 및 저장
    """
    sep = "=" * 55
    logger.info(sep)
    logger.info("🚀 미국 주식 뉴스레터 파이프라인 시작")
    logger.info(f"   실행 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(sep)

    # ── Step 1: 뉴스 수집 ────────────────────────────────────
    logger.info("[1/5] 뉴스 수집 중... (RSS 피드)")
    articles = collect_news(hours_back=12, max_articles=30)

    if not articles:
        logger.warning("수집된 기사가 없습니다. RSS 피드 연결 상태를 확인해주세요.")
        logger.warning("파이프라인 중단.")
        return

    logger.info(f"  ✓ {len(articles)}개 기사 수집 완료")

    # ── Step 2: AI 인사이트 생성 (Gemini Flash) ───────────────
    logger.info("[2/5] AI 인사이트 생성 중... (Gemini 1.5 Flash)")
    insights = generate_insights(articles)
    logger.info(f"  ✓ 요약 {len(insights.summary_points)}개 포인트 생성 완료")

    # ── Step 3: Slack 초안 전송 ──────────────────────────────
    logger.info("[3/5] Slack 초안 전송 중...")
    slack_message = format_slack_message(articles, insights)
    message_ts = send_draft(slack_message)
    logger.info(f"  ✓ Slack 전송 완료 (ts={message_ts})")

    # ── Step 4: 승인 대기 (최대 30분, 폴링) ──────────────────
    logger.info("[4/5] 사용자 승인 대기 중... (✅ 이모지 또는 스레드 코멘트)")
    approved, user_comment = wait_for_approval(
        message_ts=message_ts,
        poll_interval=60,       # 60초마다 체크
        timeout_minutes=30,     # 30분 후 자동 승인
    )

    if approved:
        logger.info(f"  ✓ ✅ 사용자 승인됨")
        if user_comment:
            logger.info(f"  📝 코멘트: {user_comment}")
    else:
        logger.info("  ⏰ 타임아웃 → 자동 승인으로 처리")

    # ── Step 5: HTML 뉴스레터 생성 및 저장 ──────────────────
    logger.info("[5/5] HTML 뉴스레터 생성 중...")
    html = build_newsletter_html(articles, insights, user_comment=user_comment)
    output_path = save_newsletter(html)

    logger.info(sep)
    logger.info("✅ 파이프라인 완료!")
    logger.info(f"   결과물: {output_path}")
    logger.info(f"   로그:   {log_file}")
    logger.info(sep)


def run_scheduled() -> None:
    """
    schedule 라이브러리를 사용하여 매일 08:00 KST에 파이프라인 실행.
    로컬 환경 전용 (GitHub Actions에서는 사용 불필요).
    KST = UTC+9 → UTC 23:00 (전날) = 로컬에서 schedule은 시스템 시간 기준.
    """
    import schedule
    import time

    logger.info("📅 스케줄 모드 시작 — 매일 08:00 KST에 실행됩니다.")
    logger.info("   (종료하려면 Ctrl+C)")

    # 시스템 시간이 KST인 경우
    schedule.every().day.at("08:00").do(run_pipeline)

    # 즉시 1회 테스트 실행 (원하면 주석 해제)
    # run_pipeline()

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="미국 주식 뉴스레터 자동화 파이프라인"
    )
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="스케줄 모드 (매일 08:00 KST 자동 실행). 미설정 시 즉시 1회 실행.",
    )
    args = parser.parse_args()

    if args.schedule:
        run_scheduled()
    else:
        run_pipeline()
