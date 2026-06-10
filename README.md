# ПАМЯТКА ПО ПРОЕКТУ
python scripts/batch_parse_yandex_objects.py
python -m src.main evaluate-quality
python -m src.main build-corpus
python -m src.main train-model
python -m src.main predict-sentiment
python -m src.db.load_processed_to_postgres


## 1. Открыть проект

```powershell
cd C:\Users\User\Pictures\Проекты\tourist_reviews_project
```

## 2. Включить виртуальное окружение

```powershell
.venv\Scripts\activate
```

Если окружение не создано:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 3. Проверить Git

```powershell
git status
```

Нормально, если:

```text
nothing to commit, working tree clean
```

---

# ПАРСИНГ ОБЪЕКТОВ ЯНДЕКС

## 4. Файл со списком объектов

Файл:

```text
data/input/yandex_objects_50.csv
```

Формат:

```csv
name,city,type,url,limit,scrolls
ШҚО сәулет-этнографиялық музейі,Өскемен,museum,https://yandex.kz/maps/org/arkhitekturno_etnograficheskiy_i_prirodno_landshaftnyy_muzey_zapovednik/52858059805/reviews/?ll=82.621910%2C49.947096&z=17,100,25
Hayat Hospitality Oskemen,Өскемен,hotel,https://yandex.kz/maps/org/dedeman/10030744167/reviews/?ll=82.627280%2C49.941815&z=19.16,400,180
Парк Жастар,Өскемен,recreation,https://yandex.kz/maps/org/jastar_sayaba_/34943060736/reviews/?ll=67.717773%2C47.789769&z=18,400,150
Надпись Рухани жаңғыру,Өскемен,attraction,https://yandex.kz/maps/org/rukhani_zhangghyru_zhazuy/156038790292/reviews/?ll=82.649358%2C49.981988&z=13,100,25
```

Типы объектов:

```text
museum
hotel
attraction
restaurant
recreation
cultural_object
```

Настройка количества отзывов:

```text
limit 100  → scrolls 25–35
limit 250  → scrolls 70–100
limit 400  → scrolls 150–220
```

## 5. Очистить CSV от пробелов

```powershell
python -c "import pandas as pd; p='data/input/yandex_objects_50.csv'; df=pd.read_csv(p, encoding='utf-8-sig'); df.columns=df.columns.astype(str).str.replace('\ufeff','',regex=False).str.strip(); df=df.map(lambda x: x.strip() if isinstance(x,str) else x); df.to_csv(p,index=False,encoding='utf-8-sig'); print(df.to_string())"
```

Проверить колонки:

```powershell
python -c "import pandas as pd; df=pd.read_csv('data/input/yandex_objects_50.csv', encoding='utf-8-sig'); print([repr(c) for c in df.columns])"
```

Должно быть:

```text
['name', 'city', 'type', 'url', 'limit', 'scrolls']
```

## 6. Запустить парсинг

```powershell
python scripts/batch_parse_yandex_objects.py
```

Если ошибка `No module named 'src'`:

```powershell
python -m scripts.batch_parse_yandex_objects
```

## 7. Проверить количество собранных отзывов

```powershell
python -c "import pandas as pd; o=pd.read_csv('data/processed/objects_processed.csv'); r=pd.read_csv('data/processed/reviews_processed.csv'); print('Objects:', len(o)); print('Reviews:', len(r)); print(r.groupby(['source','source_object_id']).size().reset_index(name='count').to_string())"
```

Пример результата:

```text
Objects: 4
Reviews: 371

source  source_object_id  count
yandex       10030744167    300
yandex       34943060736     48
yandex       52858059805     19
yandex      156038790292      4
```

## 8. Проверить raw JSON одного объекта

```powershell
python -c "import json; from pathlib import Path; p=Path('data/raw/yandex/yandex_10030744167_reviews.json'); d=json.loads(p.read_text(encoding='utf-8')); print('RAW:', len(d.get('reviews', [])))"
```

---

# ОБРАБОТКА ДАННЫХ

## 9. Посчитать качество данных

```powershell
python -m src.main evaluate-quality
```

Результат:

```text
data/processed/quality_report.csv
```

## 10. Создать корпус отзывов

```powershell
python -m src.main build-corpus
```

Результат:

```text
data/processed/corpus_reviews.csv
```

## 11. Обучить модель тональности

```powershell
python -m src.main train-model
```

Результаты:

```text
models/sentiment_model.pkl
models/tfidf_vectorizer.pkl
data/processed/model_report.json
```

## 12. Предсказать тональность

```powershell
python -m src.main predict-sentiment
```

Результат:

```text
data/processed/sentiment_predictions.csv
```

---

# ЗАГРУЗКА В БД

## 13. Загрузить данные в PostgreSQL / Supabase

```powershell
python -m src.db.load_processed_to_postgres
```

Нормальный результат:

```text
Reviews loaded/updated: ...
Reviews skipped because object was not found: 0
Review analysis inserted: ...
Review analysis skipped: ...
Upload to PostgreSQL completed.
```

Главное:

```text
Reviews skipped because object was not found: 0
```

---

# ПОЛНЫЙ ЦИКЛ ПОСЛЕ ИЗМЕНЕНИЯ CSV

```powershell
python -c "import pandas as pd; p='data/input/yandex_objects_50.csv'; df=pd.read_csv(p, encoding='utf-8-sig'); df.columns=df.columns.astype(str).str.replace('\ufeff','',regex=False).str.strip(); df=df.map(lambda x: x.strip() if isinstance(x,str) else x); df.to_csv(p,index=False,encoding='utf-8-sig'); print(df.to_string())"

python scripts/batch_parse_yandex_objects.py

python -c "import pandas as pd; o=pd.read_csv('data/processed/objects_processed.csv'); r=pd.read_csv('data/processed/reviews_processed.csv'); print('Objects:', len(o)); print('Reviews:', len(r)); print(r.groupby(['source','source_object_id']).size().reset_index(name='count').to_string())"

python -m src.main evaluate-quality
python -m src.main build-corpus
python -m src.main train-model
python -m src.main predict-sentiment
python -m src.db.load_processed_to_postgres
```

---

# STREAMLIT

## 14. Запустить сайт локально

```powershell
python -m streamlit run src/dashboard/app.py
```

Адрес:

```text
http://localhost:8501
```

## 15. Если Streamlit показывает старые данные

```powershell
streamlit cache clear
python -m streamlit run src/dashboard/app.py
```

В браузере нажать:

```text
Ctrl + F5
```

---

# SUPABASE SQL

## 16. Проверить объекты и количество отзывов

```sql
SELECT 
    o.name,
    o.type,
    o.city,
    r.source,
    r.source_object_id,
    COUNT(*) AS reviews_count
FROM reviews r
JOIN tourist_objects o ON o.id = r.object_id
GROUP BY o.name, o.type, o.city, r.source, r.source_object_id
ORDER BY reviews_count DESC;
```

## 17. Проверить общее количество отзывов

```sql
SELECT COUNT(*) AS reviews_count
FROM reviews;
```

## 18. Проверить тональность

```sql
SELECT sentiment_label, COUNT(*)
FROM review_analysis
GROUP BY sentiment_label
ORDER BY sentiment_label;
```

## 19. Проверить города

```sql
SELECT city, COUNT(*)
FROM tourist_objects
GROUP BY city
ORDER BY city;
```

## 20. Исправить город

```sql
UPDATE tourist_objects
SET city = 'Өскемен'
WHERE city IN (
    'Усть-Каменогорск',
    'Усть Каменогорск',
    'Каменогорск',
    'Оскемен',
    'Oskemen',
    'Ust-Kamenogorsk',
    'Ust Kamenogorsk'
);
```

## 21. Исправить sequence, если ошибка duplicate key

```sql
SELECT setval(
    pg_get_serial_sequence('tourist_objects', 'id'),
    COALESCE((SELECT MAX(id) FROM tourist_objects), 1),
    true
);

SELECT setval(
    pg_get_serial_sequence('reviews', 'id'),
    COALESCE((SELECT MAX(id) FROM reviews), 1),
    true
);

SELECT setval(
    pg_get_serial_sequence('review_analysis', 'id'),
    COALESCE((SELECT MAX(id) FROM review_analysis), 1),
    true
);
```

---

# GIT

## 22. Проверить изменения

```powershell
git status
```

## 23. Добавить файлы

```powershell
git add README.md
git add src/dashboard/app.py
git add scripts/batch_parse_yandex_objects.py
git add data/input/yandex_objects_50.csv
git add data/processed/objects_processed.csv
git add data/processed/reviews_processed.csv
git add data/processed/quality_report.csv
git add data/processed/corpus_reviews.csv
git add data/processed/sentiment_predictions.csv
git add data/processed/model_report.json
```

## 24. Commit

```powershell
git commit -m "Update project data and commands"
```

## 25. Push

```powershell
git pull --rebase origin main
git push
```

## 26. Проверить после push

```powershell
git status
```

---

# НЕ ДОБАВЛЯТЬ В GITHUB

```text
.env
.venv/
.idea/
__pycache__/
data/debug/
data/raw/yandex/
.streamlit/secrets.toml
```

Если случайно добавлено:

```powershell
git restore --staged .env
git restore --staged data/debug/
git restore --staged data/raw/yandex/
git restore --staged .streamlit/secrets.toml
```

---

# .GITIGNORE

```gitignore
.env
.streamlit/secrets.toml

.venv/
.idea/
__pycache__/
*.pyc

data/debug/*
!data/debug/.gitkeep

data/raw/yandex/
```

---

# КОРОТКИЙ ПОРЯДОК ДЛЯ 4 ОБЪЕКТОВ

```powershell
python scripts/batch_parse_yandex_objects.py
python -m src.main evaluate-quality
python -m src.main build-corpus
python -m src.main train-model
python -m src.main predict-sentiment
python -m src.db.load_processed_to_postgres
python -m streamlit run src/dashboard/app.py
```

---

# КОРОТКИЙ ПОРЯДОК ДЛЯ 50 ОБЪЕКТОВ

1. Дополнить файл:

```text
data/input/yandex_objects_50.csv
```

2. Запустить:

```powershell
python -c "import pandas as pd; p='data/input/yandex_objects_50.csv'; df=pd.read_csv(p, encoding='utf-8-sig'); df.columns=df.columns.astype(str).str.replace('\ufeff','',regex=False).str.strip(); df=df.map(lambda x: x.strip() if isinstance(x,str) else x); df.to_csv(p,index=False,encoding='utf-8-sig'); print(df.to_string())"
python scripts/batch_parse_yandex_objects.py
python -m src.main evaluate-quality
python -m src.main build-corpus
python -m src.main train-model
python -m src.main predict-sentiment
python -m src.db.load_processed_to_postgres
```

---

# АКАДЕМИЧЕСКОЕ ОПИСАНИЕ ДЛЯ ДИПЛОМА

```text
Деректерді жинау кезеңінде туристік нысандар бойынша Яндекс Карталар платформасындағы пайдаланушы пікірлері Selenium негізіндегі парсер арқылы алынады. Әр туристік нысан үшін атауы, қаласы, түрі, дереккөз сілтемесі және пікірлерді жинау параметрлері CSV файлында беріледі. Жиналған пікірлер бастапқы түрде raw JSON/CSV форматында сақталып, кейін тазарту және нормалау кезеңінен өтеді. Өңдеу барысында мәтіндік өрістер тазаланады, рейтингтер бір шкалаға келтіріледі, пікір тілі анықталады, қайталанатын және сапасыз жазбалар белгіленеді. Дайын деректер PostgreSQL дерекқорына жүктеліп, тоналдылықты анықтау нәтижелері review_analysis кестесінде сақталады. Соңғы кезеңде Streamlit негізіндегі веб-интерфейс арқылы туристік нысандар, пікірлер, рейтингтер, сапа көрсеткіштері және тоналдылық нәтижелері визуализацияланады.
```
