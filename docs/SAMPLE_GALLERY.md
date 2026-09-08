# Sample Gallery — real generated audio

Every audio file here and every number in this table was produced by `scripts/generate_samples.py` calling the real running backend (`oddadmix/lahgtna-omnivoice-v2`, run locally) — nothing hand-typed or invented. Re-run the script to regenerate after any pipeline change.

## 1. الفصحى (MSA)

### فصحى قياسية (`msa_01`)

- **النص المُدخل:** التكنولوجيا الحديثة تُغيّر طريقة تواصل الناس مع بعضهم البعض حول العالم.
- **اللهجة:** `msa` — النبرة: `moderate pitch`
- **زمن التوليد:** 4846ms لصوت مدته 5600ms (RTF 0.87)
- **الملف الصوتي:** [`audio/samples/msa_01.wav`](audio/samples/msa_01.wav)

## 2. لهجة عامية

### سعودية (نجدية) عامية (`dialect_saudi_01`)

- **النص المُدخل:** وش عندك اليوم؟ يا ليت تجي نتقهوى شوي عند أبوي بعد صلاة العصر.
- **النص بعد المعالجة (تشكيل + تطبيع):** وَشّ عِنْدَك الْيَوْمَ؟ يَا لَيْت تَجِي نَتَقَهْوَى شَوِيّ عِنْد أَبَوَيّ بَعْد صَلاَة الْعَصْرِ.
- **اللهجة:** `saudi` — النبرة: `moderate pitch`
- **زمن التوليد:** 7850ms لصوت مدته 5130ms (RTF 1.53)
- **الملف الصوتي:** [`audio/samples/dialect_saudi_01.wav`](audio/samples/dialect_saudi_01.wav)
- **ملاحظة:** Colloquial Saudi phrasing the model has no MSA equivalent for ('وش', 'نتقهوى').

## 3. أسماء وكلمات صعبة

### أسماء أعلام صعبة (`difficult_names_01`)

- **النص المُدخل:** التقى دوستويفسكي بالمخرج كريشتوف كيشلوفسكي في مهرجان إشبيلية السينمائي.
- **النص بعد المعالجة (تشكيل + تطبيع):** الْتَقَى دُوسْتُوَيْفِسْكِيٌّ بِالْمَخْرَجِ كَرِيشْتُوفَ كَيْشَلُوفَسْكِيٍّ فِي مِهْرَجَانِ إِشْبِيلِيَّةَ السِّينَمَائِيِّ.
- **اللهجة:** `msa` — النبرة: `moderate pitch`
- **زمن التوليد:** 9634ms لصوت مدته 6000ms (RTF 1.61)
- **الملف الصوتي:** [`audio/samples/difficult_names_01.wav`](audio/samples/difficult_names_01.wav)
- **ملاحظة:** Transliterated foreign proper nouns (Dostoevsky, Krzysztof Kieślowski) — the classic mispronunciation source item 3 demonstrates fixing via pronunciation_overrides.json.

## 4. أرقام وتواريخ وعملات واختصارات وكلمات إنجليزية

### أرقام وتواريخ وعملات واختصارات وكلمات إنجليزية (`mixed_content_01`)

- **النص المُدخل:** اجتمع د. أحمد يوم 15 مارس 2024 الساعة 3:30 مساءً، ودفع 250 ريال سعودي مقابل اشتراك Netflix عبر تطبيق iPhone الجديد.
- **النص بعد المعالجة (تشكيل + تطبيع):** اجتمع د. أحمد يوم خمسة عشر مارس ألفان و أربعة و عشرون الساعة ثلاثة:ثلاثون مساءً، ودفع مئتان و خمسون ريال سعودي مقابل اشتراك Netflix عَبْرُ تَطْبِيقٍ iPhone الْجَدِيدِ.
- **اللهجة:** `msa` — النبرة: `moderate pitch`
- **زمن التوليد:** 11409ms لصوت مدته 13440ms (RTF 0.85)
- **الملف الصوتي:** [`audio/samples/mixed_content_01.wav`](audio/samples/mixed_content_01.wav)
- **ملاحظة:** Number, date, time, currency, an honorific abbreviation (د.), two English brand words.

## 5. نفس الجملة بأنماط/نبرات مختلفة

### محايد (نبرة متوسطة) (`style_neutral`)

- **النص المُدخل:** أنا سعيد جدًا بلقائك اليوم، وأتمنى أن نتعاون قريبًا.
- **اللهجة:** `msa` — النبرة: `moderate pitch`
- **زمن التوليد:** 3721ms لصوت مدته 4600ms (RTF 0.81)
- **الملف الصوتي:** [`audio/samples/style_neutral.wav`](audio/samples/style_neutral.wav)

### حماس (نبرة عالية جدًا) (`style_excited`)

- **النص المُدخل:** أنا سعيد جدًا بلقائك اليوم، وأتمنى أن نتعاون قريبًا.
- **اللهجة:** `msa` — النبرة: `very high pitch`
- **زمن التوليد:** 3719ms لصوت مدته 4080ms (RTF 0.91)
- **الملف الصوتي:** [`audio/samples/style_excited.wav`](audio/samples/style_excited.wav)

### هدوء (نبرة منخفضة جدًا) (`style_calm_low`)

- **النص المُدخل:** أنا سعيد جدًا بلقائك اليوم، وأتمنى أن نتعاون قريبًا.
- **اللهجة:** `msa` — النبرة: `very low pitch`
- **زمن التوليد:** 3718ms لصوت مدته 4600ms (RTF 0.81)
- **الملف الصوتي:** [`audio/samples/style_calm_low.wav`](audio/samples/style_calm_low.wav)

### همس (`style_whisper`)

- **النص المُدخل:** أنا سعيد جدًا بلقائك اليوم، وأتمنى أن نتعاون قريبًا.
- **اللهجة:** `msa` — النبرة: `low pitch` — همس
- **زمن التوليد:** 3731ms لصوت مدته 4600ms (RTF 0.81)
- **الملف الصوتي:** [`audio/samples/style_whisper.wav`](audio/samples/style_whisper.wav)
