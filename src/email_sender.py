"""
이메일 발송 모듈 — Resend API
- 무료 플랜: 월 3,000건 / 일 100건
- API 키 하나로 즉시 사용 가능
- 발급: https://resend.com → Sign up → API Keys
"""
import os
import logging
from datetime import datetime

import resend
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
EMAIL_FROM     = os.getenv("EMAIL_FROM", "onboarding@resend.dev")  # 도메인 인증 전 기본값
EMAIL_TO       = os.getenv("EMAIL_TO", "")
PAGES_BASE_URL = os.getenv("PAGES_BASE_URL", "")


def send_newsletter_email(html: str, output_path: str = "") -> bool:
    """
    완성된 HTML 뉴스레터를 Resend API로 발송.
    성공 시 True, 실패 시 False 반환 (파이프라인 중단 없음).
    """
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY가 설정되지 않았습니다. 이메일 발송 건너뜀.")
        return False

    if not EMAIL_TO:
        logger.warning("EMAIL_TO가 설정되지 않았습니다. 이메일 발송 건너뜀.")
        return False

    today = datetime.now().strftime("%Y년 %m월 %d일")
    subject = f"📰 {today} 미국 주식 뉴스레터"

    # GitHub Pages 링크가 있으면 이메일 상단에 "웹에서 보기" 배너 삽입
    if PAGES_BASE_URL:
        web_banner = (
            f'<div style="text-align:center;background:#1e293b;padding:12px;">'
            f'<a href="{PAGES_BASE_URL}" '
            f'style="color:#94a3b8;font-family:sans-serif;font-size:13px;text-decoration:none;">'
            f'🔗 웹에서 보기</a></div>'
        )
        html = html.replace("<body>", f"<body>\n{web_banner}", 1)

    try:
        resend.api_key = RESEND_API_KEY

        response = resend.Emails.send({
            "from": EMAIL_FROM,
            "to": [EMAIL_TO],
            "subject": subject,
            "html": html,
        })

        email_id = response.get("id", "unknown")
        logger.info(f"이메일 발송 완료 → {EMAIL_TO} (id: {email_id})")
        return True

    except Exception as e:
        logger.error(f"이메일 발송 실패: {e}")
        return False
