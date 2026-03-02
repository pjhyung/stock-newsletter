"""
이메일 발송 모듈 — Resend API
- 수신자 목록: subscribers.txt (한 줄에 이메일 하나)
- 무료 플랜: 월 3,000건 / 일 100건
- 발급: https://resend.com → API Keys
"""
import os
import logging
from pathlib import Path
from datetime import datetime

import resend
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
EMAIL_FROM     = os.getenv("EMAIL_FROM", "onboarding@resend.dev")
PAGES_BASE_URL = os.getenv("PAGES_BASE_URL", "")

SUBSCRIBERS_FILE = Path(__file__).parent.parent / "subscribers.txt"


def load_subscribers() -> list[str]:
    """
    subscribers.txt에서 활성 이메일 목록을 읽어 반환.
    # 주석 줄과 빈 줄은 자동으로 제외.
    """
    if not SUBSCRIBERS_FILE.exists():
        logger.warning(f"subscribers.txt 파일이 없습니다: {SUBSCRIBERS_FILE}")
        return []

    emails = []
    for line in SUBSCRIBERS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            emails.append(line)

    logger.info(f"구독자 {len(emails)}명 로드 완료")
    return emails


def send_newsletter_email(html: str, output_path: str = "") -> bool:
    """
    subscribers.txt의 모든 구독자에게 뉴스레터 발송.
    한 명이라도 성공하면 True 반환.
    """
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY가 설정되지 않았습니다. 이메일 발송 건너뜀.")
        return False

    subscribers = load_subscribers()
    if not subscribers:
        logger.warning("구독자가 없습니다. subscribers.txt를 확인해주세요.")
        return False

    today = datetime.now().strftime("%Y년 %m월 %d일")
    subject = f"📰 {today} 미국 주식 뉴스레터"

    # GitHub Pages "웹에서 보기" 배너
    if PAGES_BASE_URL:
        web_banner = (
            f'<div style="text-align:center;background:#1e293b;padding:12px;">'
            f'<a href="{PAGES_BASE_URL}" '
            f'style="color:#94a3b8;font-family:sans-serif;font-size:13px;text-decoration:none;">'
            f'🔗 웹에서 보기</a></div>'
        )
        html_with_banner = html.replace("<body>", f"<body>\n{web_banner}", 1)
    else:
        html_with_banner = html

    resend.api_key = RESEND_API_KEY
    success_count = 0

    for email in subscribers:
        try:
            response = resend.Emails.send({
                "from": EMAIL_FROM,
                "to": [email],
                "subject": subject,
                "html": html_with_banner,
            })
            logger.info(f"  발송 완료 → {email} (id: {response.get('id', '?')})")
            success_count += 1

        except Exception as e:
            logger.error(f"  발송 실패 → {email}: {e}")

    logger.info(f"이메일 발송 결과: {success_count}/{len(subscribers)}명 성공")
    return success_count > 0
