# Lessons Learned

_Updated after user corrections. Rules to prevent repeating mistakes._

---

## 2026-03-11: Permissions patří do settings.local.json, ne do paměti

**Chyba:** Když uživatel udělí trvalý souhlas s příkazem (např. `bash(cat:*)`), zapsal jsem to jen do MEMORY.md jako poznámku — ale to nemá žádný reálný efekt na povolování.

**Pravidlo:** Trvalé souhlasy s příkazy VŽDY zapisovat do `.claude/settings.local.json` → `permissions.allow`. Paměť je jen referenční — settings.local je to, co skutečně řídí auto-approve.
