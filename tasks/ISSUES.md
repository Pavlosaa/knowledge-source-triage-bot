# Issues Tracker

## 📊 Přehled issues

| # | Název | Severity | Status | Datum | Fix (commit/PR) | Plán opravy |
|---|-------|----------|--------|-------|-----------------|-------------|
| 1 | Cross-ref Claude response truncation | High | 🟢 FIXED | 2026-04-04 | PR #10 (`091cccb`) | — |
| 2 | F2 discovery nefunguje — embedded_urls=0 + low-value rejection | High | 🟡 PENDING VERIFICATION | 2026-04-04 | PR #11 | — |

**Statistiky:** 2 celkem | 1 🟢 fixed | 0 🔴 open | 1 🟡 pending

---

## 🟢 FIXED Issues

### Issue #1: Cross-ref Claude response truncation

**Status:** 🟢 FIXED (PR #10)
**Discovered:** 2026-04-04
**Reporter:** User
**Severity:** High

**Problém:**
Při cross-referencování nového záznamu prošlo 57-97 kandidátů přes tag/topic overlap filtr. Claude Haiku s max_tokens=500 nestíhal vygenerovat kompletní JSON odpověď — výstup byl oříznut uprostřed stringu → `Unterminated string starting at: line 21 column 17` → žádné cross-reference se nezapsaly.

**Reprodukce:**
- Poslat do Telegram bota URL na tweet s běžnými tagy (LLM, AI, Claude apod.)
- Příklad: `https://x.com/karpathy/status/2040470801506541998`
- V logu: `Cross-ref: 57 candidates passed overlap filter` → `Cross-reference Claude response parse failed`

**Expected behavior:**
Cross-reference by měl zapsat relevantní relace do Notion. Při velkém počtu kandidátů by měl vybrat top N a Haiku by měl mít dostatek tokenů na odpověď.

**Fix:** PR #10 — kandidáti rankováni podle overlap score (tags×1 + topics×2), cap na top 15, max_tokens zvýšen na 1000.

---

## 🟡 PENDING VERIFICATION

### Issue #2: F2 discovery nefunguje — embedded_urls=0 + low-value rejection

**Status:** 🟡 PENDING VERIFICATION (PR #11)
**Discovered:** 2026-04-04
**Reporter:** User
**Severity:** High

**Problém:**
F2 GitHub repo discovery nefunguje pro tweety s GitHub odkazy. Dva root causes:

1. **embedded_urls=0:** ScrapFly HTML parser neextrahuje GitHub URL z tweet card expanderů. Tweety obsahují GitHub linky jako t.co redirecty v link card preview, ne jako plaintext v těle tweetu. Parser vrací `text_len=18 embedded_urls=0`.

2. **Low-value rejection blokuje discovery:** Krátký tweet (18 znaků, např. "Check this out 👇") je v Phase 2 zamítnut jako `has_value=False`. Discovery orchestrátor (`run_pipeline_with_discovery`) se spustí až po pipeline, ale kontroluje `has_value` a `fetched_content` — pokud parent nemá hodnotu, discovery se nespustí.

**Reprodukce:**
- Poslat do Telegram bota tweet s GitHub linkem: `https://x.com/githubprojects/status/2039274105778970934`
- V logu: `Parsed tweet: text_len=18 embedded_urls=0` → `has_value=False` → žádná discovery

**Expected behavior:**
Bot by měl extrahovat GitHub URL z tweetu (i z link card), analyzovat odkazované repo, a vytvořit Notion záznam. Discovery by měla proběhnout i když parent tweet je low-value.

**Fix:** PR #11 — dvě změny:
1. `twitter.py`: extrahovat href z `card.wrapper` `<a>` tagů (link preview cards)
2. `extractor.py`: resolve t.co shortlinks přes HTTP HEAD redirect → získat finální GitHub URL
3. `extractor.py` je nyní `async` (kvůli HTTP resolve)
