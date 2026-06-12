# University Application Tracker 🎓

A comprehensive, full-stack Django web application designed to help students manage their higher education applications, scholarships, required documents, test scores, and deadlines in one centralized dashboard.

This project demonstrates production-ready backend patterns including relational database design, background task queues, external API integration, caching, automated email notifications, and secure file sharing.

---

## 🚀 Features

### 1. Authentication & Security
* Secure user registration, login, and logout using Django's built-in authentication system.
* Site-wide privacy: every view is protected with `@login_required` to ensure data isolation per user.

### 2. University Management (Full CRUD)
* Log and manage universities with fields for Name, Country, Program, Type (*Reach / Match / Safety*), Status, Deadline, Website, and Notes.
* Advanced list view equipped with text search (Name/Country/Program) and multi-attribute filtering.
* Dynamic "days-until-deadline" counter that changes color visually when a deadline becomes urgent.
* Per-university score requirements (`avg_sat`, `min_ielts`, `min_toefl`) used for dynamic admissions chance calculation.

### 3. Smarter Admissions Chances
* Each university stores its own average SAT, minimum IELTS, and minimum TOEFL requirements.
* The application dynamically compares the user's actual scores against each university's specific thresholds — not hardcoded global minimums.
* Results are labeled contextually: *High probability*, *Good chance*, *Competitive*, *Reach — strong app needed*, and *Reach — scores below target*.
* A university with no requirements set is treated favorably so unresearched entries don't unfairly penalise the user.

### 4. Scholarship Tracking
* Track financial aid opportunities linked directly to specific university applications.
* Monitor amounts, currencies, application status, and individual deadlines.
* View a global, aggregated list of all scholarships across all institutions.

### 5. Document Management, Versioning & Secure Sharing
* Securely upload supporting documents (*SOP, LOR, Transcripts, CV, Essays*) per university or as general assets.
* **Document versioning**: each document supports multiple file uploads representing drafts and revisions (e.g. *Draft 1*, *Revised*, *Final*) without losing previous versions.
* **Reviewer share links**: generate secure, temporary, view-only URLs (configurable 1–30 day expiry) for any document — shareable with counselors or teachers without requiring an account.
* Share links track access count, can be revoked instantly, and display an expiry page when no longer valid.
* Full document center featuring type badges, upload timestamps, file downloads, version history, and safe deletions.

### 6. Test Score Tracking
* Input and manage standardized test scores: **SAT** (Reading & Writing + Math, auto-calculated totals), **IELTS** (Overall + 4 bands), and **TOEFL iBT** (Total + 4 sections).
* **Score validation** enforced at three layers — model validators, cross-field form logic, and HTML input constraints:
  * SAT sections clamped to 200–800 in 10-point increments.
  * IELTS bands clamped to 0.0–9.0 in 0.5 increments; overall band is validated against the mean of the four skill scores (±0.5 tolerance).
  * TOEFL sections clamped to 0–30 each; total must equal the exact sum of all four sections.
* Visual progress bars on the dashboard displaying performance metrics.

### 7. Interactive Dashboard & Analytics
* High-level statistical cards summarizing total applications, submissions, interviews, acceptances, and urgent deadlines.
* **Deadline timeline chart**: horizontal bar chart showing days until each deadline, color-coded red (overdue), amber (< 30 days), and purple (upcoming).
* **Application type donut chart**: visual breakdown of Reach / Match / Safety distribution.
* **Scholarship budget chart**: side-by-side comparison of total scholarships applied for versus total awarded, in USD.
* Chronologically sorted upcoming deadlines with priority color coding.

### 8. Application Task Checklists
* Every university automatically receives a pre-populated task checklist on creation, scaled by type:
  * *Safety*: 7 core tasks (SOP, LOR x2, transcripts, CV, test scores).
  * *Match*: core + supplemental essay and financial documents.
  * *Reach*: match tasks + short-answer essays, sponsorship proof, and visa preparation.
* Tasks can be toggled, updated, added, deleted, and regenerated individually per university.

### 9. Automated Deadline Reminders (Celery + Redis)
* A scheduled asynchronous worker runs daily at **08:00 AM** via `django-celery-beat`.
* Automatically scans for upcoming deadlines exactly **30, 14, and 7 days** away.
* Dispatches HTML emails using Django's `send_mail()` with a 3-tier retry mechanism for fail-safes.
* Intelligently skips applications already marked as *Accepted* or *Rejected*.
* Switches to a console backend seamlessly during local development.

### 10. Live University Autocomplete (API & Scraping)
* Real-time search functionality when adding universities (triggers after typing 2+ characters).
* Fetches live data from the **Hipolabs Universities API**.
* Results are cached locally via **Redis** for 1 hour to optimize performance and prevent rate limiting.
* Implements a **BeautifulSoup4** web scraper fallback to enrich metadata if needed.

---

## 🛠️ Tech Stack

| Layer | Technology / Framework |
| :--- | :--- |
| **Backend Framework** | Django 4.2 (Python) |
| **Database** | SQLite (Local Development) |
| **Task Queue** | Celery 5 |
| **Message Broker & Cache** | Redis 7 |
| **Periodic Schedule** | django-celery-beat |
| **Frontend Charts** | Chart.js 4 |
| **HTML Scraping** | BeautifulSoup4 + Requests |
| **Authentication** | Django Built-in Auth System |

---

## 📦 Project Architecture

The project utilises a clean, decoupled two-app layout:
* `core/`: Handles global project configurations, routing, settings, and Celery worker initializations.
* `universities/`: Houses the main application architecture including Models, Views, Forms, Context Processors, Asynchronous Tasks, and Template tags.

---

## 🔧 Setup & Installation

### Prerequisites
Ensure you have the following installed on your machine:
* Python 3.10+
* Redis Server (running on `localhost:6379`)

### Step-by-Step Guide

1. **Clone the repository:**
```bash
   git clone git@github.com:davlatbekzoirov/UniTracker.git
   cd university-application-tracker
```

2. **Create and activate a virtual environment:**
```bash
   python -m venv venv
   source venv/bin/activate        # macOS / Linux
   venv\Scripts\activate           # Windows
```

3. **Install dependencies:**
```bash
   pip install -r requirements.txt
```

4. **Apply migrations:**
```bash
   python manage.py migrate
```

5. **Start the development server:**
```bash
   python manage.py runserver
```

6. **Start Celery worker and beat scheduler** (separate terminals):
```bash
   celery -A core worker -l info
   celery -A core beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```