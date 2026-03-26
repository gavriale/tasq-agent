import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MAX_DAILY_TOKENS = int(os.getenv("MAX_DAILY_TOKENS", 50000))

CANDIDATE_PROFILE = """
Name: Gavri Ale
Role: Backend Software Engineer (4 years experience)
Education: BSc Computer Science, Open University Israel
Location: Israel (Tel Aviv area preferred)
Open to: Backend Engineer, Full Stack, AI Engineer, Platform Engineer
Not interested in: Frontend-only, QA, DevOps-only roles

Skills: Python, backend systems, APIs, databases
Strong interest in: AI/ML engineering roles
"""

LINKEDIN_RSS_FEEDS = [
    "https://www.linkedin.com/jobs/search/?keywords=backend+engineer&location=Israel&f_TPR=r10800&sortBy=DD",
    "https://www.linkedin.com/jobs/search/?keywords=python+developer&location=Tel+Aviv&f_TPR=r10800&sortBy=DD",
    "https://www.linkedin.com/jobs/search/?keywords=ai+engineer&location=Israel&f_TPR=r10800&sortBy=DD",
    "https://www.linkedin.com/jobs/search/?keywords=software+engineer&location=Tel+Aviv&f_TPR=r10800&sortBy=DD",
]

RSS_POLL_INTERVAL_HOURS = 3
DAILY_TIP_HOUR = 9  # 9am Israel time (Asia/Jerusalem)
FOLLOW_UP_DAYS = 7
