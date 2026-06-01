# tourist_reviews_project

Дипломный проект: **«Разработка системы анализа и визуализации пользовательских отзывов для оценки туристических объектов»**.

Проект представлен как информационная система полного цикла обработки отзывов:

```text
Сыртқы дереккөздер
→ деректерді жинау және импорттау
→ raw сақтау
→ preprocessing
→ PostgreSQL
→ corpus builder
→ ML Analysis Module
→ dashboard / visualization
```

## Важное ограничение по источникам данных

Проект не позиционируется как инструмент свободного обхода ограничений закрытых платформ. Для диплома и реализации корректная формулировка такая:

> Пікір мәтіндері рұқсат етілген API, экспорт, CSV/JSON импорт немесе ашық датасеттер арқылы қабылданады.

2GIS используется преимущественно для списка объектов и справочной информации. Яндекс Карты и Google Maps рассматриваются как источники отзывов только в рамках разрешённых API, экспорта, CSV/JSON импорта или открытых датасетов.

## Архитектура

Система разделена на слои:

1. Сыртқы дереккөздер қабаты.
2. Деректерді жинау және импорттау қабаты.
3. Алдын ала өңдеу қабаты.
4. Деректерді сақтау қабаты.
5. Талдау қабаты.
6. Визуализация және пайдаланушы қабаты.

Подробные диаграммы находятся в папке `docs/diagrams` в формате Mermaid.

## Структура проекта

```text
tourist_reviews_project/
  data/
    raw/
    processed/
    logs/
  database/
    schema.sql
  models/
  src/
    config.py
    main.py
    db/
    parsers/
    importers/
    preprocessing/
    reconciliation/
    corpus/
    ml/
    dashboard/
  notebooks/
  docs/
  requirements.txt
  README.md
  .env.example
  .gitignore
```

## Быстрый запуск локально

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Для демонстрационной обработки sample-данных без подключения к PostgreSQL:

```bash
python -m src.main run-sample-pipeline
```

После выполнения появятся файлы:

```text
data/processed/objects_processed.csv
data/processed/reviews_processed.csv
data/processed/corpus_reviews.csv
data/processed/quality_report.csv
data/processed/sentiment_predictions.csv
```

Запуск dashboard:

```bash
streamlit run src/dashboard/app.py
```

Если `DATABASE_URL` не задан, dashboard читает демонстрационные CSV-файлы из `data/processed`.

## PostgreSQL

Схема БД находится в:

```text
database/schema.sql
```

Для локальной базы:

```bash
psql -U postgres -d tourist_reviews -f database/schema.sql
```

Для Supabase SQL можно выполнить через SQL Editor.

## Streamlit Community Cloud + Supabase

Рекомендуемая схема развёртывания:

```text
GitHub → Streamlit Community Cloud → Supabase PostgreSQL
```

Пароли и connection string нельзя хранить в GitHub. Для Streamlit Cloud используйте `secrets.toml`:

```toml
DATABASE_URL="postgresql+psycopg2://USER:PASSWORD@HOST:5432/postgres"
```

Веб-интерфейс предназначен для интерактивного анализа уже подготовленных данных, а не для запуска тяжёлого Selenium-парсинга в браузере.

## ML-модуль

В базовой версии используется классический подход:

```text
text_cleaned → TF-IDF → Logistic Regression → sentiment_label / sentiment_score
```

Если размеченного корпуса нет, модуль может сформировать демонстрационные weak labels на основе нормализованного рейтинга. Для диплома это нужно описывать осторожно: как прототипный или базовый механизм, а не как окончательно обученная промышленная модель.

## Основные команды

```bash
# Полный demo pipeline
python -m src.main run-sample-pipeline

# Только preprocessing sample-данных
python -m src.main preprocess-sample

# Сформировать корпус
python -m src.main build-corpus

# Посчитать качество данных
python -m src.main evaluate-quality

# Обучить демонстрационную модель
python -m src.main train-model

# Получить предсказания тональности
python -m src.main predict-sentiment
```

## Что показывать на защите

- слойную архитектуру;
- ER-модель PostgreSQL;
- сценарий взаимодействия модулей;
- raw → processed → corpus pipeline;
- quality_report.csv;
- corpus_reviews.csv;
- Streamlit dashboard;
- sentiment distribution;
- фильтры по городу, типу объекта, языку и тональности.
