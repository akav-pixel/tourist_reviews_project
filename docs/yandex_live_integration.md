# Yandex live parser integration

Бұл модуль Яндекс Карталар пікірлерін алу/импорттау қабатын негізгі дипломдық жүйеге бөлек ingestion pipeline ретінде қосады.

Маңызды архитектуралық қағида:

```text
Yandex ingestion pipeline → raw сақтау → preprocessing → corpus → ML → PostgreSQL / dashboard
```

Streamlit dashboard Selenium парсингті тікелей іске қоспайды. Dashboard тек PostgreSQL немесе processed CSV нәтижелерін оқиды.

## Жергілікті іске қосу

```powershell
python -m src.main parse-yandex `
  --url "YANDEX_OBJECT_REVIEWS_URL" `
  --name "Нысан атауы" `
  --city "Өскемен" `
  --type "cultural_object" `
  --limit 100 `
  --scrolls 25 `
  --visible `
  --debug-html
```

Нәтижелер:

```text
data/raw/yandex/yandex_<oid>_reviews_all.csv
data/raw/yandex/yandex_<oid>_raw.json
data/processed/yandex_<oid>_reviews_normalized.csv
data/processed/reviews_processed.csv
data/processed/objects_processed.csv
data/processed/quality_report.csv
data/processed/corpus_reviews.csv
data/processed/sentiment_predictions.csv
```

## Дипломда қолданылатын сақ формулировка

Пікір мәтіндері рұқсат етілген API, экспорт, CSV/JSON импорт немесе ашық датасеттер арқылы қабылданады. Веб-интерфейс деректерді жинау процесін тікелей орындауға емес, алдын ала өңделген және PostgreSQL дерекқорында сақталған нәтижелерді интерактивті түрде талдауға бағытталған.
