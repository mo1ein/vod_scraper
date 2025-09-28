# 🎬  VOD Scraper

A sophisticated data pipeline that intelligently crawls multiple Video-on-Demand platforms, normalizes content metadata, and exposes unified data through a RESTful API with advanced content matching capabilities.

---

## Architecture
```mermaid
graph TB
    A[VOD Platform 1] --> B[Scrapy Spider]
    X[VOD Platform 2] --> B
    Y[VOD Platform N] --> B
    
    B --> F[Content Matcher]
    F --> G[Redis]
    F --> PostgreSQL[(PostgreSQL)]
    B --> C[Data Pipeline]
    C[Data Pipeline] --> PostgreSQL[(PostgreSQL)]
    C[Data Pipeline] --> G[Redis]


    PostgreSQL[(PostgreSQL)] --> I[Django REST API]
    I --> J[Client]
    
    subgraph "Core match logic"
        F --> K[Exact Matching]
        F --> L[Fuzzy Logic]
        F --> N[Title Variations]
    end
    
    subgraph "Data Storage"
        G
        PostgreSQL[(PostgreSQL)]
    end
    
    style F fill:blue
    style I fill:#20aa76
    style PostgreSQL fill:#699eca
```

---


### 🔧 Run
```bash
git clone https://github.com/mo1ein/vod_scraper.git
cd vod_scraper
```
Then:
```bash
make env
make build
make up
```
Now you can enjoy the app. <br />

### 🌐 Endpoints

```bash
curl http://localhost:8000/movies/
```

```bash
curl http://localhost:8000/series/
```
```bash
curl http://localhost:8000/items/<id>/
```
