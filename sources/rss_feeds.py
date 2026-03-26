import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import List

from db.database import is_job_seen, mark_job_seen

SECRET_TELAVIV_URL = "https://jobs.secrettelaviv.com/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


@dataclass
class Job:
    url: str
    title: str
    company: str
    location: str
    summary: str


def _scrape_secret_telaviv() -> List[Job]:
    """Scrape job listings from jobs.secrettelaviv.com."""
    try:
        response = requests.get(SECRET_TELAVIV_URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"[Scraper] Failed to fetch Secret Tel Aviv Jobs: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    rows = soup.select("div.wpjb-grid-row")
    jobs = []

    for row in rows:
        # Title + URL
        title_tag = row.select_one("span.wpjb-line-major a")
        if not title_tag:
            continue
        url = title_tag.get("href", "").strip()
        title = title_tag.get_text(strip=True)

        # Company
        company_tag = row.select_one("span.wpjb-sub.wpjb-sub-small")
        company = company_tag.get_text(strip=True) if company_tag else ""

        # Location
        location_tag = row.select_one("span.wpjb-glyphs")
        location = location_tag.get_text(strip=True) if location_tag else ""

        if url:
            jobs.append(Job(url=url, title=title, company=company, location=location, summary=""))

    return jobs


def fetch_new_jobs() -> List[Job]:
    """
    Scrape Secret Tel Aviv Jobs.
    Returns only jobs not yet seen (deduped via DB).
    Marks new jobs as seen before returning.
    """
    jobs = _scrape_secret_telaviv()
    new_jobs = []

    for job in jobs:
        if not is_job_seen(job.url):
            mark_job_seen(job.url, title=job.title, company=job.company)
            new_jobs.append(job)

    print(f"[Scraper] Found {len(new_jobs)} new jobs out of {len(jobs)} total listings.")
    return new_jobs


if __name__ == "__main__":
    from db.database import init_db
    init_db()
    jobs = fetch_new_jobs()
    for job in jobs:
        print(f"  - {job.title} @ {job.company} | {job.location}")
