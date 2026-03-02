<!-- Generated: 2026-03-02 | Files scanned: 17 | Token estimate: ~580 -->

# Data & Configuration Codemap

**Files:** config.py, prompts.py, writer.py, projects.py | **Updated:** 2026-03-02

---

## Configuration & Environment Variables

### Required at Startup (bot/config.py)

```python
class Config(frozen=True):
  # Telegram (required)
  telegram_bot_token: str          # from @BotFather
  telegram_group_id: int           # group numeric ID (can be negative)

  # X.com / Twitter authentication (required for twikit)
  twitter_username: str            # @username
  twitter_password: str            # account password
  twitter_email: str               # email associated with account

  # Claude AI (required)
  anthropic_api_key: str           # from console.anthropic.com

  # Notion (required)
  notion_api_key: str              # from notion.so/my-integrations
  notion_rnd_page_id: str          # ICT Project R&D Resources page ID
  notion_projects_page_id: str     # Projects page ID (for context cache)

  # GitHub (optional, for higher rate limit)
  github_token: str | None         # from github.com/settings/tokens
```

### Loading & Validation

```python
def load_config() → Config:
  ├─ Load from .env via python-dotenv
  ├─ For each required var:
  │  └─ os.getenv(key) → validate not empty
  ├─ Parse TELEGRAM_GROUP_ID as int
  ├─ Collect errors list
  ├─ If errors: log each, raise SystemExit
  └─ Return Config dataclass (immutable)
```

**Failure behavior:**
- Missing any required var → immediately exit with error list
- No silent failures, no defaults

**File:** `.env.example` (template for onboarding)

---

## Analysis Data Structures

### AnalysisResult (bot/analyzer/pipeline.py)

```python
@dataclass
class AnalysisResult:
  # Always populated
  url: str                    # original URL from Telegram message
  has_value: bool             # true = valuable, false = rejected

  # Valuable source (populated if has_value=true)
  title: str | None           # Generated or extracted, max 80 chars
  core_summary: str | None    # 2-3 sentences, no BS
  key_principles: list[str]   # Extracted principles
  use_cases: list[str]        # How to apply/use
  discovery_score: int | None # 1-5 rating
  tags: list[str]             # Free-form tags
  project_recommendations: list[dict]  # [{"project_name": str, "relevance": "high|medium|low", "how_to_apply": str}]
  notion_url: str | None      # Created page URL (or None if write failed)

  # Rejected source (populated if has_value=false)
  brief_summary: str | None   # One-liner summary (nullable)
  rejection_reason: str | None # Why not worth attention

  # Classification & credibility (both paths)
  topic: str | None           # One of TOPICS list
  credibility_score: int | None # 1-5 source credibility
  credibility_reason: str | None # Why that score
```

**Flow:**
```
URL
 ↓
[Fetcher] → Content dataclass
 ↓
[Phase 1: Credibility] → credibility_score, credibility_reason
 ↓
[Phase 2: Value Check] → has_value, (rejection_reason?)
 ├─ if has_value=true:
 │   [Phase 3A: Full Analysis Sonnet]
 │   ↓
 │   title, core_summary, key_principles, use_cases,
 │   discovery_score, tags, topic, project_recommendations
 │   ↓
 │   [Notion Writer]
 │   ↓
 │   notion_url
 │
 └─ if has_value=false:
     [Phase 3B: Rejection Summary Haiku]
     ↓
     brief_summary, topic
```

---

## Claude Analysis Prompts

### Phase 1: Credibility Check (claude-haiku-4-5)

**Input:**
- Author name
- Author username
- Follower count
- Verified status (for tweets)
- Text snippet

**System Prompt:** `CREDIBILITY_SYSTEM` (bot/analyzer/prompts.py)
```
You are an expert at evaluating credibility of online sources.
Respond ONLY with valid JSON matching:
{"credibility_score": <1-5>, "credibility_reason": "<one sentence>"}
```

**Output:** `AnalysisResult.credibility_score`, `credibility_reason`

---

### Phase 2: Value Assessment (claude-haiku-4-5)

**Input:**
- Full fetched content

**System Prompt:** `VALUE_ASSESSMENT_SYSTEM`
```
You are a critical evaluator of technical content.
You ignore marketing hype, buzzwords, repetition.
You reward concrete insights, novel techniques, actionable information.
Respond ONLY with valid JSON:
{"has_value": <true|false>, "value_score": <1-5>, "rejection_reason": "<reason or null>"}
```

**Output:** `AnalysisResult.has_value`, (optional) `rejection_reason`

---

### Phase 3A: Full Analysis (claude-sonnet-4-6, if has_value=true)

**Input:**
- Full content
- Project context from ProjectsCache (user's existing projects)

**System Prompt:** `FULL_ANALYSIS_SYSTEM`
```
You are a technical analyst. Extract real value, discard filler.
You know user's projects and can recommend how findings apply.

Title rules (priority):
  1. Use explicit name if exists (repo name, article title)
  2. Otherwise generate max-80-char title from core content
  3. Title must be factual, describe what it DOES (not hype)

Topic — pick exactly one:
  - "AI Tools & Libraries"
  - "Educational Content"
  - "Tips & Tricks"
  - "Best Practices"
  - "News & Updates"
  - "Interesting Findings"

Respond ONLY with valid JSON:
{
  "title": "<string, max 80 chars>",
  "topic": "<one of topics above>",
  "core_summary": "<2-3 sentences without BS>",
  "key_principles": ["<string>"],
  "use_cases": ["<string>"],
  "discovery_score": <1-5>,
  "tags": ["<string>"],
  "project_recommendations": [
    {
      "project_name": "<string>",
      "relevance": "<high|medium|low>",
      "how_to_apply": "<string>"
    }
  ]
}
```

**Output:** title, core_summary, key_principles, use_cases, discovery_score, tags, topic, project_recommendations

---

### Phase 3B: Rejection Summary (claude-haiku-4-5, if has_value=false)

**Input:**
- Full content

**System Prompt:** `REJECTION_SUMMARY_SYSTEM`
```
You are a concise technical summarizer.
Respond ONLY with valid JSON:
{"brief_summary": "<one sentence or null>", "rejection_reason": "<why not worth attention>"}
```

**Output:** `brief_summary`, `rejection_reason`

---

## Notion Database Schema

### AI Sources Database

**Auto-created by NotionWriter** under specified parent page.

**Properties:**

| Property | Type | Cardinality | Values/Constraints | Source |
|----------|------|-------------|------|--------|
| Title | title | 1 | string, max 80 | result.title or url[:80] |
| Topic | select | 1 | "AI Tools & Libraries", "Educational Content", "Tips & Tricks", "Best Practices", "News & Updates", "Interesting Findings" | result.topic |
| Discovery Score | number | 1 | 1–5 (integer) | result.discovery_score |
| Source URL | url | 1 | valid HTTP(S) URL | original_url |
| Content Type | select | 1 | "Tweet", "X Article", "GitHub", "Article" | fetcher type inference |
| Author | rich_text | 1 | string | fetcher-extracted author (if available) |
| Tags | multi_select | many | user-generated tags | result.tags[:10] |
| Date Added | date | 1 | YYYY-MM-DD | datetime.now(UTC).date() |
| Relevant Projects | multi_select | many | project names from context | project_recommendations (high/medium only) |

**Color Coding:**

Topic select colors:
```python
{
  "AI Tools & Libraries": "blue",
  "Educational Content": "green",
  "Tips & Tricks": "yellow",
  "Best Practices": "purple",
  "News & Updates": "red",
  "Interesting Findings": "orange",
}
```

Content Type select colors:
```python
{
  "Tweet": "blue",
  "X Article": "green",
  "GitHub": "gray",
  "Article": "orange",
}
```

### Page Body Blocks

If `result.has_value=true`, page body includes:

```
H2: 📌 Core Summary
└─ Paragraph: result.core_summary (capped 2000 chars per block)

H2: 🔑 Key Principles
├─ Bullet: key_principles[0]
├─ Bullet: key_principles[1]
└─ ... (each capped 2000 chars)

H2: 💡 Use Cases
├─ Bullet: use_cases[0]
├─ Bullet: use_cases[1]
└─ ...

H2: 🎯 Relevance for Projects
├─ Toggle: "Project A — HIGH"
│  └─ Paragraph: how_to_apply
├─ Toggle: "Project B — MEDIUM"
│  └─ Paragraph: how_to_apply
└─ ...

H2: 🔗 Source
└─ Bookmark: source_url (Notion will fetch metadata)
```

---

## Content Fetcher Data Structures

### Tweet Content (bot/fetcher/twitter.py)

```python
@dataclass
class TweetContent:
  tweet_id: str           # numeric ID from URL
  author_name: str        # display name
  author_username: str    # @username
  follower_count: int     # follower count
  is_verified: bool       # blue check
  text: str               # full tweet text
  embedded_urls: list[str] # URLs mentioned in tweet
```

### Article Content (bot/fetcher/article.py, twitter.py)

```python
@dataclass
class ArticleContent:
  url: str                # original URL
  title: str | None       # page title (or None)
  author_name: str | None # article author (or None)
  body: str               # full article body text
```

### Repository Content (bot/fetcher/github.py)

```python
@dataclass
class RepoContent:
  owner: str              # GitHub user/org
  repo: str               # repository name
  description: str | None # repo description
  stars: int              # star count
  language: str | None    # primary language (or None)
  readme: str | None      # README.md content (or None)
```

### Page Content (bot/fetcher/playwright.py)

```python
@dataclass
class PageContent:
  url: str                # original URL
  title: str | None       # page title (or None)
  body: str               # visible body text
```

---

## Project Context Cache

### ProjectsCache (bot/notion/projects.py)

**Data Lifecycle:**

```
Telegram handler
 ↓
[Phase 3A needs context]
 ↓
ProjectsCache.get_context() → string
 ├─ If stale (> 24 hours) or empty:
 │   ├─ Fetch Projects page from Notion
 │   ├─ Extract child_page blocks (each = one project)
 │   ├─ For each project: fetch first text block
 │   └─ Build context string:
 │      "User's existing projects:
 │       - Project A: Description (max 300 chars)
 │       - Project B: Description
 │       ..."
 │
 └─ Return cached string
    (stale context kept if fetch fails)

TTL: 86,400 seconds (24 hours)
Lock: asyncio.Lock() (concurrent requests safe)
```

**Context usage in Phase 3A prompt:**
- Injected directly into user message
- Enables Claude to recommend relevant projects
- Improves project_recommendations accuracy

---

## Telegram Response Formatting

### Valuable Source

```
🔗 <a href="https://original.url">Původní zdroj</a>

✅ <b>Hodnotný zdroj</b> | ★★★★☆ (4/5)

📌 <b>Obsah:</b> {core_summary}

🔑 <b>Klíčové body:</b>
• {key_principles[0]}
• {key_principles[1]}
...

💡 <b>Use cases:</b>
• {use_cases[0]}
• {use_cases[1]}
...

🎯 <b>Relevantní pro:</b> Project A, Project B

📖 <a href="https://notion.url">Otevřít v Notion →</a>
```

### Rejected Source

```
🔗 <a href="https://original.url">Původní zdroj</a>

❌ <b>Nízká hodnota</b>

💭 <b>Shrnutí:</b> {brief_summary}

🚫 <b>Proč:</b> {rejection_reason}
```

### Error Response

```
⚠️ Analýza selhala: {ExceptionName}. Zkus znovu nebo kontaktuj správce.
```

---

## Data Flow Summary

```
User URL
  ↓
[Handler] → extract_urls() → asyncio.Queue
  ↓
[Pipeline Orchestrator]
  ├─ Detect content type via URL regex
  ├─ Fetch content via type-specific fetcher
  ├─ Phase 1 (Haiku): credibility_score, credibility_reason
  ├─ Phase 2 (Haiku): has_value, rejection_reason?
  │
  ├─ if has_value:
  │  ├─ Load project context (cache, 24h TTL)
  │  ├─ Phase 3A (Sonnet): full analysis + project recs
  │  ├─ Notion Writer: create page + return notion_url
  │  └─ AnalysisResult complete
  │
  └─ else:
     ├─ Phase 3B (Haiku): brief_summary, rejection_reason
     └─ AnalysisResult complete
        ↓
[Formatter] → HTML string
        ↓
[Telegram Reply] → user response
```
