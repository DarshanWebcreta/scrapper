# AeroLeads: Universal Lead Intelligence & Dynamic Web Scraping Platform

A production-grade, fully dynamic B2B discovery, crawling, extraction, classification, and lead intelligence platform. Enter any query topic, select countries/industries, choose custom fields to extract, and AeroLeads automatically:
1. Generates 5 search queries dynamically (via AI Query Planner).
2. Discovers business listings and domains across multiple source adapters (DuckDuckGo, Europages, ThomasNet, IndiaMART, YellowPages).
3. Crawls company homepages and key subpages (/about, /contact, etc.) concurrently.
4. Normalizes, cleans, and deduplicates domains, emails, and phone numbers.
5. Performs category/industry classification (AI-based with fallback rules).
6. Dynamically extracts structured custom metadata fields (e.g. CEO, founder, revenue, employee count) using local AI prompting.
7. Exports results to CSV, JSON, and Microsoft Excel (XLSX).

---

## Technology Stack

- **Backend**: Python 3.10 FastAPI
- **Frontend**: React + Vite
- **Scraping**: Playwright, BeautifulSoup4, HTTPX, lxml, extruct, trafilatura
- **AI**: Local Ollama (fallback to regex rule engines)
- **Database**: PostgreSQL (Docker mode) or SQLite (local python fallback)
- **Deployment**: Docker & docker-compose

---

## Getting Started

### Prerequisites
- Docker & docker-compose installed.
- (Optional but recommended) [Ollama](https://ollama.com/) running locally with a model pulled (e.g. `llama3` or `mistral`).

---

### Run with Docker Compose (PostgreSQL Database)

To run the entire full-stack application (frontend + backend + PostgreSQL database) inside Docker:

1. **Launch services**:
   ```bash
   docker-compose up --build
   ```
2. **Access the Frontend Dashboard**:
   Open your browser at `http://localhost:5173`.
3. **Access the Backend API Documentation**:
   Open `http://localhost:8000/docs` to see Swagger documentation.

*Note: The backend container will automatically connect to your local Ollama server at `http://host.docker.internal:11434` if it is running on your host system. Make sure Ollama is open!*

---

### Run Locally (Without Docker, SQLite Database)

For simple local development with SQLite fallback:

1. **Start Local Ollama**:
   Ensure Ollama is running on your machine:
   ```bash
   ollama run llama3
   ```

2. **Run Backend (FastAPI)**:
   ```bash
   cd backend
   pip install -r requirements.txt
   playwright install chromium
   
   # Run development server
   uvicorn app.main:app --reload --port 8000
   ```

3. **Run Frontend (Vite/React)**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   Open `http://localhost:5173` to access the dashboard.

---

## Platform Features

### 1. Dynamic User Input & Custom Schemas
Define any query topic and a list of target countries. Select standard extraction fields or write in custom keys like `CEO`, `funding`, `revenue`, `certifications`, or `products`. The system will automatically build an extraction schema and crawl for those fields using local AI content parsing.

### 2. Plugin Source Adapters
Contains modular plugin search scripts:
- `duckduckgo.py`: queries DuckDuckGo HTML directly.
- `europages.py`: crawls Europages supplier directories.
- `thomasnet.py`: parses ThomasNet listings.
- `indiamart.py`: parses IndiaMART listing pages.
- `yellowpages.py`: extracts local directory listing targets.
Adapters are selected dynamically based on query matching. If a specialized directory gets blocked by Cloudflare, the system automatically falls back to general DuckDuckGo search queries.

### 3. Smart Anti-Blocking & Concurrent Crawler
Uses Playwright with randomized User-Agent rotation, viewport scaling, and redirect handlers. Crawls the homepage and up to 3 contact/about/team subpages concurrently using an `asyncio.Semaphore` bounded by the user-defined concurrency limit.

### 4. Normalized Deduplication & Storage
Extracts emails, phone numbers, WhatsApp links, and social profile links. Cleans domains, phone formats, and country codes. Deduplicates leads by domain, email, and phone before committing to the database to ensure clean, high-quality data.

### 5. Dynamic Dashboard UI
A premium dark-themed SaaS interface with real-time SSE activity monitoring logs, query planners, historical scrape job controls, filtering, paging, and single-click CSV/JSON/Excel export managers.
