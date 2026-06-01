from __future__ import annotations
from urllib.parse import quote_plus

import os
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine, text


ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = ROOT / 'data' / 'processed'
REVIEWS_PROCESSED_CSV = PROCESSED_DIR / 'reviews_processed.csv'
OBJECTS_PROCESSED_CSV = PROCESSED_DIR / 'objects_processed.csv'
SENTIMENT_PREDICTIONS_CSV = PROCESSED_DIR / 'sentiment_predictions.csv'
QUALITY_REPORT_CSV = PROCESSED_DIR / 'quality_report.csv'

st.set_page_config(
    page_title='Tourist Reviews Analytics',
    page_icon='🏛️',
    layout='wide',

)
QUALITY_COLUMNS_RU = {
    "metric": "Показатель",
    "formula": "Формула",
    "numerator": "Числитель",
    "denominator": "Знаменатель",
    "value": "Значение",
}

REVIEWS_COLUMNS_RU = {
    "city": "Город",
    "type": "Тип объекта",
    "name": "Название объекта",
    "source": "Источник",
    "author": "Автор",
    "text_cleaned": "Очищенный текст отзыва",
    "rating_normalized": "Нормализованная оценка",
    "language": "Язык",
    "quality_status": "Статус качества",
    "sentiment_label": "Тональность",
}

TYPE_LABELS_RU = {
    "museum": "Музей",
    "hotel": "Отель",
    "attraction": "Достопримечательность",
    "restaurant": "Ресторан",
    "recreation": "Зона отдыха",
}

QUALITY_STATUS_RU = {
    "valid": "Пригоден",
    "limited": "Ограниченно пригоден",
    "rejected": "Отклонён",
}

SENTIMENT_RU = {
    "positive": "Положительная",
    "neutral": "Нейтральная",
    "negative": "Отрицательная",
}

def get_database_url() -> str | None:
    try:
        if "DATABASE_URL" in st.secrets:
            return st.secrets["DATABASE_URL"]

        if "postgres" in st.secrets:
            cfg = st.secrets["postgres"]

            user = cfg["user"]
            password = quote_plus(cfg["password"])
            host = cfg["host"]
            port = cfg["port"]
            database = cfg["database"]
            sslmode = cfg.get("sslmode", "require")

            return (
                f"postgresql+psycopg2://{user}:{password}"
                f"@{host}:{port}/{database}?sslmode={sslmode}"
            )

    except Exception:
        pass

    return os.getenv("DATABASE_URL")


@st.cache_data(show_spinner=False)
def load_from_csv() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not REVIEWS_PROCESSED_CSV.exists():
        return pd.DataFrame(), pd.DataFrame()

    reviews = pd.read_csv(REVIEWS_PROCESSED_CSV)
    objects = pd.read_csv(OBJECTS_PROCESSED_CSV) if OBJECTS_PROCESSED_CSV.exists() else pd.DataFrame()
    sentiment = pd.read_csv(SENTIMENT_PREDICTIONS_CSV) if SENTIMENT_PREDICTIONS_CSV.exists() else pd.DataFrame()

    df = reviews.copy()
    if not objects.empty and 'source_object_id' in df.columns:
        keep = [c for c in ['source_object_id', 'name', 'type', 'city', 'latitude', 'longitude'] if c in objects.columns]
        df = df.merge(objects[keep], on='source_object_id', how='left')
    if not sentiment.empty and 'review_id' in sentiment.columns:
        keep = [c for c in ['review_id', 'sentiment_label', 'sentiment_score'] if c in sentiment.columns]
        df = df.merge(sentiment[keep], on='review_id', how='left')
    return df, load_quality_report()


@st.cache_data(show_spinner=False)
def load_from_db(database_url: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    engine = create_engine(database_url, pool_pre_ping=True)
    sql = text("""
        SELECT
            r.review_id,
            r.author,
            r.review_text,
            r.text_cleaned,
            r.rating,
            r.rating_normalized,
            r.review_date,
            r.language,
            r.quality_status,
            r.is_duplicate,
            r.source,
            o.name,
            o.type,
            o.city,
            o.latitude,
            o.longitude,
            a.sentiment_label,
            a.sentiment_score
        FROM reviews r
        JOIN tourist_objects o ON o.id = r.object_id
        LEFT JOIN review_analysis a ON a.review_id = r.id
    """)
    with engine.connect() as conn:
        df = pd.read_sql_query(sql, conn)
    return df, load_quality_report()


def load_quality_report() -> pd.DataFrame:
    if QUALITY_REPORT_CSV.exists():
        return pd.read_csv(QUALITY_REPORT_CSV)
    return pd.DataFrame()


def multiselect_filter(df: pd.DataFrame, column: str, label: str) -> pd.DataFrame:
    if column not in df.columns or df[column].dropna().empty:
        return df
    values = sorted(df[column].dropna().astype(str).unique())
    selected = st.sidebar.multiselect(label, values, default=values)
    if selected:
        return df[df[column].astype(str).isin(selected)]
    return df


def main() -> None:
    st.title('Жүйе анализа и визуализации отзывов туристических объектов')
    st.caption('Данные читаются из PostgreSQL или из демонстрационных CSV-файлов, если DATABASE_URL не задан.')

    database_url = get_database_url()
    try:
        if database_url:
            df, quality = load_from_db(database_url)
            st.success('Источник данных: PostgreSQL')
        else:
            df, quality = load_from_csv()
            st.info('Источник данных: CSV demo fallback')
    except Exception as exc:
        st.warning(f'Не удалось прочитать PostgreSQL, используется CSV fallback. Причина: {exc}')
        df, quality = load_from_csv()

    if df.empty:
        st.error('Нет данных для отображения. Запустите: python -m src.main run-sample-pipeline')
        return

    st.sidebar.header('Фильтры')
    filtered = df.copy()
    filtered = multiselect_filter(filtered, 'city', 'Город')
    filtered = multiselect_filter(filtered, 'type', 'Тип объекта')
    filtered = multiselect_filter(filtered, 'language', 'Язык')
    filtered = multiselect_filter(filtered, 'quality_status', 'Статус качества')
    filtered = multiselect_filter(filtered, 'sentiment_label', 'Тональность')

    col1, col2, col3, col4 = st.columns(4)
    col1.metric('Туристические объекты', int(filtered.get('source_object_id', filtered.get('name')).nunique()))
    col2.metric('Отзывы', len(filtered))
    avg_rating = filtered['rating_normalized'].mean() if 'rating_normalized' in filtered.columns else None
    col3.metric('Средний рейтинг', f'{avg_rating:.2f}' if pd.notna(avg_rating) else '—')
    valid_share = (filtered.get('quality_status') == 'valid').mean() if 'quality_status' in filtered.columns else None
    col4.metric('Доля valid', f'{valid_share:.1%}' if pd.notna(valid_share) else '—')

    st.subheader('Распределение рейтингов')
    if 'rating_normalized' in filtered.columns:
        fig = px.histogram(filtered, x='rating_normalized', nbins=10, title='Rating normalized')
        st.plotly_chart(fig, use_container_width=True)

    left, right = st.columns(2)
    with left:
        st.subheader('Распределение языков')
        if 'language' in filtered.columns:
            fig = px.pie(filtered, names='language', title='Language distribution')
            st.plotly_chart(fig, use_container_width=True)
    with right:
        st.subheader('Распределение тональности')
        if 'sentiment_label' in filtered.columns and filtered['sentiment_label'].notna().any():
            fig = px.bar(
                filtered['sentiment_label'].fillna('unknown').value_counts().reset_index(),
                x='sentiment_label',
                y='count',
                title='Sentiment distribution',
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info('Нет результатов sentiment analysis. Запустите predict-sentiment.')

    st.subheader('Качество данных')
    if not quality.empty:
        quality_display = quality.rename(columns=QUALITY_COLUMNS_RU)
        st.dataframe(quality_display, use_container_width=True)
    else:
        st.info('quality_report.csv пока не найден.')

    st.subheader('Таблица отзывов')
    columns = [
        'city', 'type', 'name', 'source', 'author', 'text_cleaned',
        'rating_normalized', 'language', 'quality_status', 'sentiment_label'
    ]
    columns = [c for c in columns if c in filtered.columns]
    reviews_display = filtered[columns].copy()

    if "type" in reviews_display.columns:
        reviews_display["type"] = reviews_display["type"].replace(TYPE_LABELS_RU)

    if "quality_status" in reviews_display.columns:
        reviews_display["quality_status"] = reviews_display["quality_status"].replace(QUALITY_STATUS_RU)

    if "sentiment_label" in reviews_display.columns:
        reviews_display["sentiment_label"] = reviews_display["sentiment_label"].replace(SENTIMENT_RU)

    reviews_display = reviews_display.rename(columns=REVIEWS_COLUMNS_RU)

    st.dataframe(reviews_display, use_container_width=True, height=420)

if __name__ == '__main__':
    main()
