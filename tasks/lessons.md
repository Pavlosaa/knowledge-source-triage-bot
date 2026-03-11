# Lessons Learned

_Updated after user corrections. Rules to prevent repeating mistakes._

---

## 2026-03-11: Permissions patří do settings.local.json, ne do paměti

**Chyba:** Když uživatel udělí trvalý souhlas s příkazem (např. `bash(cat:*)`), zapsal jsem to jen do MEMORY.md jako poznámku — ale to nemá žádný reálný efekt na povolování.

**Pravidlo:** Trvalé souhlasy s příkazy VŽDY zapisovat do `.claude/settings.local.json` → `permissions.allow`. Paměť je jen referenční — settings.local je to, co skutečně řídí auto-approve.

## 2026-03-11: Po nastavení branch protection nepoušovat přímo do main

**Chyba:** Nastavil jsem branch protection (PR povinný, CI checks) a hned poté pushoval docs commit přímo do main (admin bypass). Porušil jsem vlastní pravidla.

**Pravidlo:** Jakmile je branch protection aktivní, VŽDY vytvořit feature branch → commit → push → PR. Žádné přímé pushy do main, ani pro "jen docs" změny.

## 2026-03-11: Číst docs nestačí — musíš je APLIKOVAT

**Chyba:** Trávím tokeny čtením docs a pravidel, ale pak je neaplikuju na vlastní práci. Nastavím branch protection a hned pushuju přímo do main. Přidám git workflow pravidla a nevšimnu si konfliktu s Core §11.

**Pravidlo:** Po každé změně pravidel/workflow se ZASTAV a zkontroluj:
1. Neporušuju právě teď to, co jsem právě nastavil?
2. Není nové pravidlo v konfliktu s existujícími?
3. Aplikuj pravidla OKAMŽITĚ, ne "od příštího commitu".
