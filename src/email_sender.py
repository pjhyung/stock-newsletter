"""
이메일 발송 모듈 (100% 무료)
- Gmail SMTP 사용 (smtplib — Python 표준 라이브러리, 추가 설치 없음)
- 생성된 HTML을 그대로 이메일 바디로 전송
"""
import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

GMAIL_USER     = os.getenv("GMAIL_USER", "")       # 발신 Gmail 주소
GMAIL_APP_PW   = os.getenv("GMAIL_APP_PASSWORD", "") # Gmail 앱 비밀번호
EMAIL_TO       = os.getenv("EMAIL_TO", "")          # 수신 이메일 (본인)
PAGES_BASE_URL = os.getenv("PAGES_BASE_URL", "")    # GitHub Pages URL


def send_newsletter_email(html: str, output_path: str = "") -> bool:
    """
    완성된 HTML 뉴스레터를 Gmail로 발송.
    성공 시 True, 실패 시 False 반환 (파이프라인 중단 없음).
    """
    if not all([GMAIL_USER, GMAIL_APP_PW, EMAIL_TO]):
        logger.warning("이메일 설정 미완료 (GMAIL_USER / GMAIL_APP_PASSWORD / EMAIL_TO)")
        return False

    today = datetime.now().strftime("%Y년 %m월 %d일")
    subject = f"📰 {today} 미국 주식 뉴스레터"

    # GitHub Pages 링크가 있으면 이메일 상단에 삽입
    if PAGES_BASE_URL:
        pages_link = (
            f'<p style="text-align:center;margin:0;padding:12px;background:#1e293b;'
            f'font-size:13px;">'
            f'<a href="{PAGES_BASE_URL}" style="color:#94a3b8;">🔗 웹에서 보기</a>'
            f'</p>'
        )
        # <body> 태그 바로 다음에 링크 삽입
        html = html.replace("<body>", f"<body>\n{pages_link}", 1)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_USER
    msg["To"]      = EMAIL_TO

    # HTML 파트 첨부
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PW)
            server.sendmail(GMAIL_USER, EMAIL_TO, msg.as_string())

        logger.info(f"이메일 발송 완료 → {EMAIL_TO}")
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error("Gmail 인증 실패 — 앱 비밀번호를 확인해주세요.")
    except Exception as e:
        logger.error(f"이메일 발송 실패: {e}")

    return False
