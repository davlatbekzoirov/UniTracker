# University Application Tracker 🎓

A comprehensive, full-stack Django web application designed to help students manage their higher education applications, scholarships, required documents, test scores, and deadlines in one centralized dashboard. 

This project demonstrates production-ready backend patterns including relational database design, background task queues, external API integration, caching, and automated email notifications.

---

## 🚀 Features

### 1. Authentication & Security
* Secure user registration, login, and logout using Django's built-in authentication system.
* Site-wide privacy: every view is protected with `@login_required` to ensure data isolation per user.

### 2. University Management (Full CRUD)
* Log and manage universities with fields for Name, Country, Program, Type (*Reach / Match / Safety*), Status, Deadline, Website, and Notes.
* Advanced list view equipped with text search (Name/Country/Program) and multi-attribute filtering.
* Dynamic "days-until-deadline" counter that changes color visually when a deadline becomes urgent.

### 3. Scholarship Tracking
* Track financial aid opportunities linked directly to specific university applications.
* Monitor amounts, currencies, application status, and individual deadlines.
* View a global, aggregated list of all scholarships across all institutions.

### 4. Document Management & File Uploads
* Securely upload supporting documents (*SOP, LOR, Transcripts, CV, Essays*) per university or as general assets.
* Full document center featuring type badges, upload timestamps, file downloads, and safe deletions.

### 5. Test Score Tracking
* Input and manage standardized test scores: **SAT** (Reading & Writing + Math, auto-calculated totals), **IELTS** (Overall + 4 bands), and **TOEFL iBT** (Total + 4 sections).
* Visual progress bars on the dashboard displaying performance metrics.

### 6. Interactive Dashboard & Analytics
* High-level statistical cards summarizing total applications, submissions, interviews, acceptances, and urgent tasks.
* Visual breakdown charts categorization applications by tier (*Reach / Match / Safety*).
* Chronologically sorted upcoming deadlines with priority color coding.

### 7. Automated Deadline Reminders (Celery + Redis)
* A scheduled asynchronous worker runs daily at **08:00 AM** via `django-celery-beat`.
* Automatically scans for upcoming deadlines exactly **30, 14, and 7 days** away.
* Dispatches HTML emails using Django's `send_mail()` system with a 3-tier retry mechanism for fail-safes.
* Intelligently skips applications already marked as *Accepted* or *Rejected*.
* Switches to a console backend seamlessly during local development.

### 8. Live University Autocomplete (API & Scraping)
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
| **HTML Scraping** | BeautifulSoup4 + Requests |
| **Authentication** | Django Built-in Auth System |

---

## 📦 Project Architecture

The project utilizes a clean, decoupled two-app layout:
* `core/`: Handles global project configurations, routing, settings, and Celery worker initializations.
* `universities/`: Houses the main application architecture including Models, Views, Forms, Context Processors, and Asynchronous Tasks.

---

## 🔧 Setup & Installation

### Prerequisites
Ensure you have the following installed on your machine:
* Python 3.10+
* Redis Server (Running on `localhost:6379`)

### Step-by-Step Guide

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/yourusername/university-application-tracker.git](https://github.com/yourusername/university-application-tracker.git)
   cd university-application-tracker