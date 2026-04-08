# Issues Tracker

## 📊 Přehled issues


| #   | Název                                                          | Severity | Status                  | Datum      | Fix (commit/PR)    | Plán opravy |
| --- | -------------------------------------------------------------- | -------- | ----------------------- | ---------- | ------------------ | ----------- |
| 1   | Cross-ref Claude response truncation                           | High     | 🟢 FIXED                | 2026-04-04 | PR #10 (`091cccb`) | —           |
| 2   | F2 discovery nefunguje — embedded_urls=0 + low-value rejection | High     | 🟡 PENDING VERIFICATION | 2026-04-04 | PR #12             | —           |
| 3   | ScrapFly timeout — prázdný error, žádný retry                 | Medium   | 🟢 FIXED                | 2026-04-08 | PR #12 (`79cfa05`) | —           |
| 4   | .git suffix v GitHub URL → 404 na API                         | Medium   | 🟢 FIXED                | 2026-04-08 | PR #12 (`b02180d`) | —           |
| 5   | Phase 3A API error zobrazen jako "nízká hodnota"               | Medium   | 🟢 FIXED                | 2026-04-08 | PR #12 (`e891900`) | —           |
| 6   | Rozbitý emoji ve formatter (přeskočeno ��)                     | Low      | 🟢 FIXED                | 2026-04-08 | PR #12 (`f91ac2e`) | —           |

**Statistiky:** 6 celkem | 4 🟢 fixed | 0 🔴 open | 1 🟡 pending

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

### Issue #3: ScrapFly timeout — prázdný error, žádný retry

**Status:** 🟢 FIXED (PR #12)
**Discovered:** 2026-04-08
**Reporter:** User
**Severity:** Medium

**Problém:** ScrapFly občas timeoutne po ~160s a vrátí prázdný error. Fetch se neretryuje, uživatel vidí "Zdroj nedostupný" bez kontextu.

**Fix:** PR #12 — retry 2x s exponential backoff (5s/10s), pouze na timeout/network errors. API-level errors (4xx, empty content) se neretryují.

### Issue #4: .git suffix v GitHub URL → 404 na API

**Status:** 🟢 FIXED (PR #12)
**Discovered:** 2026-04-08
**Reporter:** Logy
**Severity:** Medium

**Problém:** URL jako `github.com/owner/repo.git` projde přes `extract_repo_coords()` s repo name `repo.git` → GitHub API vrátí 404.

**Fix:** PR #12 — `extract_repo_coords()` stripuje `.git` suffix.

### Issue #5: Phase 3A API error zobrazen jako "nízká hodnota"

**Status:** 🟢 FIXED (PR #12)
**Discovered:** 2026-04-08
**Reporter:** User
**Severity:** Medium

**Problém:** Claude API overloaded (529) v Phase 3A způsobí `has_value=False` a zobrazí se "❌ Nízká hodnota" místo jasného error message.

**Fix:** PR #12 — Phase 3A failure nastaví `fetch_failed=True` + `rejection_reason="Claude API dočasně nedostupné, zkus znovu později."` → zobrazí se "⚠️ Zdroj nedostupný".

### Issue #6: Rozbitý emoji ve formatter

**Status:** 🟢 FIXED (PR #12)
**Discovered:** 2026-04-08
**Reporter:** User
**Severity:** Low

**Problém:** `��` v Telegram reply u přeskočených repozitářů.

**Fix:** PR #12 — nahrazeno `--`.

---

## 🟡 PENDING VERIFICATION

### Issue #2: F2 discovery nefunguje — embedded_urls=0 + low-value rejection

**Status:** 🟡 PENDING VERIFICATION (PR #12)
**Discovered:** 2026-04-04
**Reporter:** UsePR