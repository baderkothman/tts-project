# Arabic Test Cases

The full sample set from `backend/app/data/samples.py` (FR-038, FR-038a).
Every case's `expected_contains`/`expected_absent` is asserted by
`backend/tests/unit/test_samples.py`, which passes at 11/11 as of this
writing (run `pytest backend/tests/unit/test_samples.py -v` to reverify).

| ID | Category | Text | Expected transformation |
|---|---|---|---|
| msa-1 | MSA | التعليم هو الأساس لبناء مجتمع متقدم ومزدهر. | Unchanged formal Arabic |
| msa-2 | MSA | أعلنت الشركة عن نتائجها المالية للربع الأخير من العام. | Unchanged formal Arabic |
| dialect-egyptian-1 | Dialect | إزيك عامل إيه النهاردة؟ ... | Routed to `ar-EG` voice |
| dialect-gulf-1 | Dialect | شلونك اليوم؟ ... | Routed to `ar-AE` voice |
| pronunciation-1 | Pronunciation | طلب العلم فريضة ... | Contains `عِلْم` (diacritized) |
| numbers-1 | Numbers | 125 موظفاً، 1,250 عميلاً، 25.5%، 75% | All digits → Arabic words; no `%` remains |
| dates-1 | Dates | 27/09/2026, 2026-09-27 | Contains `سبتمبر`; no `/` remains |
| currencies-1 | Currencies | $25, 25 USD, 100 ريال, 1,250.50 دولار | Contains `دولار`, `ريال`, `سنت`; no `$`/`USD` remains |
| abbreviations-1 | Abbreviations | د. أحمد م. سارة ... API, AWS, AI | Contains `دكتور`, `مهندس` |
| code-switching-1 | Code-switching | اليوم عندنا meeting ... AI ... 3 PM. | `meeting` preserved with clean spacing |
| emotion-1 | Emotion | أهلاً وسهلاً بكم ... | Base sentence for style-comparison rendering |

## Additional documented edge cases (verified by unit tests)

- **Identifier digits** (`+96170123456`) are spoken digit-by-digit, not as one
  cardinal quantity — `test_numbers.py::test_identifier_digits_spoken_individually`.
- **Hamza / taa marbuta / alif maqsura are preserved**, never folded —
  `test_arabic_normalizer.py` (three dedicated tests).
- **Existing diacritics survive normalization unchanged** —
  `test_arabic_normalizer.py::test_diacritics_preserved`.
- **A pronunciation rule does not corrupt an unrelated word containing the
  same substring** ("معلم" / teacher vs. "علم" / knowledge) —
  `test_pronunciation.py::test_rule_does_not_fire_inside_longer_word`.
- **SSML-like text is escaped, never interpreted as markup** —
  `test_ssml_injection.py` (3 tests).
- **Stage order**: dates/currencies must run before generic number
  verbalization or their digits get consumed prematurely — this was an actual
  bug caught during implementation, fixed, and is now a regression test:
  `test_pipeline_order.py`.

Run the full offline suite: `pytest backend/tests -v -m "not integration"`.
