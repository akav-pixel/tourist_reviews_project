from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine, text


ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = ROOT / "data" / "processed"

REVIEWS_PROCESSED_CSV = PROCESSED_DIR / "reviews_processed.csv"
OBJECTS_PROCESSED_CSV = PROCESSED_DIR / "objects_processed.csv"
SENTIMENT_PREDICTIONS_CSV = PROCESSED_DIR / "sentiment_predictions.csv"
QUALITY_REPORT_CSV = PROCESSED_DIR / "quality_report.csv"


st.set_page_config(
    page_title="Tourist Reviews Analytics",
    page_icon="🏛️",
    layout="wide",
)


UI = {
    "ru": {
        "title": "Система анализа и визуализации отзывов туристических объектов",
        "caption": "Данные читаются из PostgreSQL или из демонстрационных CSV-файлов, если DATABASE_URL не задан.",
        "interface": "Язык интерфейса",
        "filters": "Фильтры",
        "city": "Город",
        "type": "Тип объекта",
        "language": "Язык",
        "quality_status": "Статус качества",
        "sentiment": "Тональность",
        "objects": "Туристические объекты",
        "reviews": "Отзывы",
        "avg_rating": "Средний рейтинг",
        "valid_share": "Доля valid",
        "rating_distribution": "Распределение рейтингов",
        "rating_distribution_title": "Распределение нормализованных оценок",
        "rating_normalized": "Нормализованная оценка",
        "review_count": "Количество отзывов",
        "language_distribution": "Распределение языков",
        "language_distribution_title": "Распределение языков отзывов",
        "sentiment_distribution": "Распределение тональности",
        "sentiment_distribution_title": "Распределение тональности отзывов",
        "quality": "Качество данных",
        "reviews_table": "Таблица отзывов",
        "source_postgres": "Источник данных: PostgreSQL",
        "source_csv": "Источник данных: CSV demo fallback",
        "postgres_warning": "Не удалось прочитать PostgreSQL, используется CSV fallback. Причина:",
        "no_data": "Нет данных для отображения. Запустите: python -m src.main run-sample-pipeline",
        "no_quality": "quality_report.csv пока не найден.",
        "no_sentiment": "Нет результатов анализа тональности. Запустите predict-sentiment.",
    },
    "kk": {
        "title": "Туристік нысандар пікірлерін талдау және визуализациялау жүйесі",
        "caption": "Деректер PostgreSQL дерекқорынан немесе DATABASE_URL берілмеген жағдайда демонстрациялық CSV файлдарынан оқылады.",
        "interface": "Интерфейс тілі",
        "filters": "Сүзгілер",
        "city": "Қала",
        "type": "Нысан түрі",
        "language": "Тіл",
        "quality_status": "Деректер сапасының мәртебесі",
        "sentiment": "Тоналдылық",
        "objects": "Туристік нысандар",
        "reviews": "Пікірлер",
        "avg_rating": "Орташа рейтинг",
        "valid_share": "Valid үлесі",
        "rating_distribution": "Рейтингтердің таралуы",
        "rating_distribution_title": "Нормаланған бағалардың таралуы",
        "rating_normalized": "Нормаланған баға",
        "review_count": "Пікірлер саны",
        "language_distribution": "Тілдердің таралуы",
        "language_distribution_title": "Пікір тілдерінің таралуы",
        "sentiment_distribution": "Тоналдылықтың таралуы",
        "sentiment_distribution_title": "Пікірлер тоналдылығының таралуы",
        "quality": "Деректер сапасы",
        "reviews_table": "Пікірлер кестесі",
        "source_postgres": "Деректер көзі: PostgreSQL",
        "source_csv": "Деректер көзі: CSV demo fallback",
        "postgres_warning": "PostgreSQL дерекқорынан оқу мүмкін болмады, CSV fallback қолданылады. Себебі:",
        "no_data": "Көрсету үшін деректер жоқ. Іске қосыңыз: python -m src.main run-sample-pipeline",
        "no_quality": "quality_report.csv файлы әзірге табылған жоқ.",
        "no_sentiment": "Тоналдылықты талдау нәтижелері жоқ. predict-sentiment іске қосыңыз.",
    },
}


LABELS = {
    "ru": {
        "columns_quality": {
            "metric": "Показатель",
            "formula": "Формула",
            "numerator": "Числитель",
            "denominator": "Знаменатель",
            "value": "Значение",
        },
        "columns_reviews": {
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
        },
        "type": {
            "museum": "Музей",
            "hotel": "Отель",
            "attraction": "Достопримечательность",
            "restaurant": "Ресторан",
            "recreation": "Зона отдыха",
            "cultural_object": "Культурный объект",
        },
        "quality_status": {
            "valid": "Пригоден",
            "limited": "Ограниченно пригоден",
            "rejected": "Отклонён",
        },
        "sentiment": {
            "positive": "Положительная",
            "neutral": "Нейтральная",
            "negative": "Отрицательная",
            "unknown": "Не определена",
        },
        "language": {
            "ru": "Русский",
            "kk": "Казахский",
            "mixed": "Смешанный",
            "unknown": "Не определён",
        },
        "quality_metric": {
            "K_tolyqtyk": "Коэффициент полноты",
            "K_tolyktyk": "Коэффициент полноты",
            "K_dubl": "Доля дубликатов",
            "K_zharamdy": "Доля пригодных записей",
            "K_unknown": "Доля неопределённого языка",
        },
        "quality_formula": {
            "N_tolyq / N_zhalpy": "N_полных / N_общих",
            "N_tolyk / N_zhalpy": "N_полных / N_общих",
            "N_dubl / N_zhalpy": "N_дубликатов / N_общих",
            "N_korpus / N_zhinalgan": "N_корпус / N_собранных",
            "N_unknown / N_zhalpy": "N_unknown / N_общих",
        },
    },
    "kk": {
        "columns_quality": {
            "metric": "Көрсеткіш",
            "formula": "Формула",
            "numerator": "Алым",
            "denominator": "Бөлім",
            "value": "Мәні",
        },
        "columns_reviews": {
            "city": "Қала",
            "type": "Нысан түрі",
            "name": "Нысан атауы",
            "source": "Дереккөз",
            "author": "Автор",
            "text_cleaned": "Тазартылған пікір мәтіні",
            "rating_normalized": "Нормаланған баға",
            "language": "Тіл",
            "quality_status": "Сапа мәртебесі",
            "sentiment_label": "Тоналдылық",
        },
        "type": {
            "museum": "Музей",
            "hotel": "Қонақүй",
            "attraction": "Көрікті орын",
            "restaurant": "Мейрамхана",
            "recreation": "Демалыс аймағы",
            "cultural_object": "Мәдени нысан",
        },
        "quality_status": {
            "valid": "Жарамды",
            "limited": "Шектеулі жарамды",
            "rejected": "Қабылданбаған",
        },
        "sentiment": {
            "positive": "Оң",
            "neutral": "Бейтарап",
            "negative": "Теріс",
            "unknown": "Анықталмаған",
        },
        "language": {
            "ru": "Орыс тілі",
            "kk": "Қазақ тілі",
            "mixed": "Аралас",
            "unknown": "Анықталмаған",
        },
        "quality_metric": {
            "K_tolyqtyk": "Толықтық коэффициенті",
            "K_tolyktyk": "Толықтық коэффициенті",
            "K_dubl": "Қайталанатын жазбалар үлесі",
            "K_zharamdy": "Жарамды жазбалар үлесі",
            "K_unknown": "Тілі анықталмаған жазбалар үлесі",
        },
        "quality_formula": {
            "N_tolyq / N_zhalpy": "N_толық / N_жалпы",
            "N_tolyk / N_zhalpy": "N_толық / N_жалпы",
            "N_dubl / N_zhalpy": "N_дубликат / N_жалпы",
            "N_korpus / N_zhinalgan": "N_корпус / N_жиналған",
            "N_unknown / N_zhalpy": "N_unknown / N_жалпы",
        },
    },
}


def get_database_url() -> str | None:
    """
    Reads PostgreSQL connection either from Streamlit Secrets or environment.

    Supported formats:
    1) DATABASE_URL = "postgresql+psycopg2://..."
    2) [postgres]
       host = "..."
       port = 6543
       database = "postgres"
       user = "..."
       password = "..."
       sslmode = "require"
    """
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
def load_quality_report() -> pd.DataFrame:
    if QUALITY_REPORT_CSV.exists():
        return pd.read_csv(QUALITY_REPORT_CSV)
    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_from_csv() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not REVIEWS_PROCESSED_CSV.exists():
        return pd.DataFrame(), pd.DataFrame()

    reviews = pd.read_csv(REVIEWS_PROCESSED_CSV)
    objects = (
        pd.read_csv(OBJECTS_PROCESSED_CSV)
        if OBJECTS_PROCESSED_CSV.exists()
        else pd.DataFrame()
    )
    sentiment = (
        pd.read_csv(SENTIMENT_PREDICTIONS_CSV)
        if SENTIMENT_PREDICTIONS_CSV.exists()
        else pd.DataFrame()
    )

    df = reviews.copy()

    if not objects.empty and "source_object_id" in df.columns:
        keep = [
            c
            for c in ["source_object_id", "name", "type", "city", "latitude", "longitude"]
            if c in objects.columns
        ]
        df = df.merge(objects[keep], on="source_object_id", how="left")

    if not sentiment.empty and "review_id" in sentiment.columns:
        keep = [
            c
            for c in ["review_id", "sentiment_label", "sentiment_score"]
            if c in sentiment.columns
        ]
        df = df.merge(sentiment[keep], on="review_id", how="left")

    return df, load_quality_report()


@st.cache_data(show_spinner=False)
def load_from_db(database_url: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    engine = create_engine(database_url, pool_pre_ping=True)

    sql = text(
        """
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
            COALESCE(a.sentiment_label, r.sentiment_label) AS sentiment_label,
            COALESCE(a.sentiment_score, r.sentiment_score) AS sentiment_score
        FROM reviews r
        JOIN tourist_objects o ON o.id = r.object_id
        LEFT JOIN review_analysis a ON a.review_id = r.id
        """
    )

    with engine.connect() as conn:
        df = pd.read_sql_query(sql, conn)

    return df, load_quality_report()


def multiselect_filter(
    df: pd.DataFrame,
    column: str,
    label: str,
    value_labels: dict[str, str] | None = None,
) -> pd.DataFrame:
    if column not in df.columns or df[column].dropna().empty:
        return df

    values = sorted(df[column].dropna().astype(str).unique())
    value_labels = value_labels or {}

    selected = st.sidebar.multiselect(
        label,
        values,
        default=values,
        format_func=lambda x: value_labels.get(str(x), str(x)),
    )

    if selected:
        return df[df[column].astype(str).isin(selected)]

    return df


def translate_column_values(
    df: pd.DataFrame,
    column: str,
    labels: dict[str, str],
) -> pd.DataFrame:
    if column in df.columns:
        df[column] = df[column].astype(str).replace(labels)
    return df


def main() -> None:
    interface_lang = st.sidebar.radio(
        "Интерфейс / Тіл",
        options=["ru", "kk"],
        format_func=lambda x: "Русский" if x == "ru" else "Қазақша",
    )

    T = UI[interface_lang]
    L = LABELS[interface_lang]

    st.title(T["title"])
    st.caption(T["caption"])

    database_url = get_database_url()

    try:
        if database_url:
            df, quality = load_from_db(database_url)
            st.success(T["source_postgres"])
        else:
            df, quality = load_from_csv()
            st.info(T["source_csv"])
    except Exception as exc:
        st.warning(f"{T['postgres_warning']} {exc}")
        df, quality = load_from_csv()

    if df.empty:
        st.error(T["no_data"])
        return

    st.sidebar.header(T["filters"])

    filtered = df.copy()
    filtered = multiselect_filter(filtered, "city", T["city"])
    filtered = multiselect_filter(filtered, "type", T["type"], L["type"])
    filtered = multiselect_filter(filtered, "language", T["language"], L["language"])
    filtered = multiselect_filter(
        filtered,
        "quality_status",
        T["quality_status"],
        L["quality_status"],
    )
    filtered = multiselect_filter(
        filtered,
        "sentiment_label",
        T["sentiment"],
        L["sentiment"],
    )

    col1, col2, col3, col4 = st.columns(4)

    if "source_object_id" in filtered.columns:
        object_count = int(filtered["source_object_id"].nunique())
    elif "name" in filtered.columns:
        object_count = int(filtered["name"].nunique())
    else:
        object_count = 0

    col1.metric(T["objects"], object_count)
    col2.metric(T["reviews"], len(filtered))

    avg_rating = (
        filtered["rating_normalized"].mean()
        if "rating_normalized" in filtered.columns and not filtered.empty
        else None
    )
    col3.metric(T["avg_rating"], f"{avg_rating:.2f}" if pd.notna(avg_rating) else "—")

    valid_share = (
        (filtered["quality_status"] == "valid").mean()
        if "quality_status" in filtered.columns and not filtered.empty
        else None
    )
    col4.metric(T["valid_share"], f"{valid_share:.1%}" if pd.notna(valid_share) else "—")

    st.subheader(T["rating_distribution"])

    if "rating_normalized" in filtered.columns:
        fig = px.histogram(
            filtered,
            x="rating_normalized",
            nbins=10,
            title=T["rating_distribution_title"],
        )
        fig.update_xaxes(title_text=T["rating_normalized"])
        fig.update_yaxes(title_text=T["review_count"])
        st.plotly_chart(fig, use_container_width=True)

    left, right = st.columns(2)

    with left:
        st.subheader(T["language_distribution"])

        if "language" in filtered.columns:
            language_display = filtered.copy()
            language_display = translate_column_values(
                language_display,
                "language",
                L["language"],
            )

            fig = px.pie(
                language_display,
                names="language",
                title=T["language_distribution_title"],
            )
            fig.update_layout(legend_title_text=T["language"])
            st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader(T["sentiment_distribution"])

        if "sentiment_label" in filtered.columns and filtered["sentiment_label"].notna().any():
            sentiment_counts = (
                filtered["sentiment_label"]
                .fillna("unknown")
                .astype(str)
                .replace(L["sentiment"])
                .value_counts()
                .reset_index()
            )

            sentiment_counts.columns = [T["sentiment"], T["review_count"]]

            fig = px.bar(
                sentiment_counts,
                x=T["sentiment"],
                y=T["review_count"],
                title=T["sentiment_distribution_title"],
            )
            fig.update_xaxes(title_text=T["sentiment"])
            fig.update_yaxes(title_text=T["review_count"])
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(T["no_sentiment"])

    st.subheader(T["quality"])

    if not quality.empty:
        quality_display = quality.copy()

        if "metric" in quality_display.columns:
            quality_display["metric"] = (
                quality_display["metric"].astype(str).replace(L["quality_metric"])
            )

        if "formula" in quality_display.columns:
            quality_display["formula"] = (
                quality_display["formula"].astype(str).replace(L["quality_formula"])
            )

        quality_display = quality_display.rename(columns=L["columns_quality"])
        st.dataframe(quality_display, use_container_width=True)
    else:
        st.info(T["no_quality"])

    st.subheader(T["reviews_table"])

    columns = [
        "city",
        "type",
        "name",
        "source",
        "author",
        "text_cleaned",
        "rating_normalized",
        "language",
        "quality_status",
        "sentiment_label",
    ]
    columns = [c for c in columns if c in filtered.columns]

    reviews_display = filtered[columns].copy()

    reviews_display = translate_column_values(reviews_display, "type", L["type"])
    reviews_display = translate_column_values(
        reviews_display,
        "quality_status",
        L["quality_status"],
    )
    reviews_display = translate_column_values(
        reviews_display,
        "sentiment_label",
        L["sentiment"],
    )
    reviews_display = translate_column_values(
        reviews_display,
        "language",
        L["language"],
    )

    reviews_display = reviews_display.rename(columns=L["columns_reviews"])

    st.dataframe(reviews_display, use_container_width=True, height=420)


if __name__ == "__main__":
    main()