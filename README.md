# 🎬  VOD Scraper

A sophisticated data pipeline that intelligently crawls multiple Video-on-Demand platforms, normalizes content metadata, and exposes unified data through a RESTful API with advanced content matching capabilities.

---

## Architecture
```mermaid
graph TB
    A[VOD Platform 1] --> B[Scrapy Spider]
    C[VOD Platform 2] --> B
    D[VOD Platform N] --> B
    
    B --> E[Content Processing Pipeline]
    E --> F[Intelligent Content Matcher]
    F --> G[Redis Cache]
    F --> H[PostgreSQL Database]
    
    H --> I[Django REST API]
    I --> J[Client Applications]
    
    subgraph "Core Intelligence"
        F --> K[Exact Matching]
        F --> L[Fuzzy Logic]
        F --> M[IMDB ID Matching]
        F --> N[Title Variations]
    end
    
    subgraph "Data Storage"
        G
        H
    end
    
    style F fill:#e1f5fe
    style H fill:#f3e5f5
    style I fill:#e8f5e8
```

```mermaid
flowchart LR
  subgraph Scrapers
    A1[Filimo Spider] -->|scraped item| B[Scrapy Items]
    A2[Namava Spider] -->|scraped item| B
  end

  B --> C[PostgreSQLPipeline]
  B --> R[Redis Cache]

  C -->|get_or_create| M[(Movie / Series)]
  C -->|create| S[(Source)]
  C --> G[Genres Table]
  C --> Cr[Credits Table]

  style Scrapers fill:#f9f,stroke:#333,stroke-width:1px
  style R fill:#f6f8fa,stroke:#333,stroke-dasharray: 2 2

  subgraph Matching
    C --> E[EnhancedContentMatcher]
    E --> M
    E --> R
  end

  subgraph API
    D[Django REST API] --> M
    D --> R
    D -->|exposes| Endpoints[/movies, /series, /items/<id>/]
  end

  DockerCompose["docker-compose (app, db, redis)"] --- Scrapers
  DockerCompose --- API
  DockerCompose --- PostgreSQL[(PostgreSQL)]
  DockerCompose --- R


```

---


### 🔧 Run
```bash
git clone ...
cd vod_scraper
```
Then:
```bash
make env
make build
make up
```
then you can enjoy the app. <br />

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
