from __future__ import annotations

import os
from html import escape
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
    page_icon="🏞️",
    layout="wide",
    initial_sidebar_state="expanded",
)

UI = {
    "ru": {
        "title": "Система анализа и визуализации отзывов туристических объектов",
        "caption": "Интерактивная панель для оценки туристических объектов на основе очищенных, нормализованных и подготовленных пользовательских отзывов.",
        "badge": "Дипломный проект",
        "filters": "Фильтры",
        "city": "Город",
        "type": "Тип объекта",
        "source": "Источник",
        "language": "Язык",
        "quality_status": "Статус качества",
        "sentiment": "Тональность",
        "objects": "Объекты",
        "reviews": "Отзывы",
        "avg_rating": "Средний рейтинг",
        "valid_share": "Доля пригодных",
        "duplicates": "Обнаружено дубликатов",
        "data_source": "Источник данных",
        "source_postgres": "PostgreSQL",
        "source_csv": "CSV demo fallback",
        "postgres_warning": "Не удалось прочитать PostgreSQL, используется CSV fallback. Причина:",
        "no_data": "Нет данных для отображения. Запустите: python -m src.main run-sample-pipeline",
        "overview": "Обзор",
        "analytics": "Аналитика",
        "quality": "Качество данных",
        "reviews_table": "Отзывы",
        "map": "Карта",
        "rating_distribution": "Распределение рейтингов",
        "rating_distribution_title": "Распределение нормализованных оценок",
        "rating_normalized": "Нормализованная оценка",
        "review_count": "Количество отзывов",
        "language_distribution": "Распределение языков",
        "language_distribution_title": "Языки отзывов",
        "sentiment_distribution": "Распределение тональности",
        "sentiment_distribution_title": "Тональность отзывов",
        "type_distribution": "Распределение по типам объектов",
        "city_distribution": "Распределение по городам",
        "source_distribution": "Распределение по источникам",
        "quality_distribution": "Распределение по статусам качества",
        "top_objects": "Топ объектов по количеству отзывов",
        "object_name": "Название объекта",
        "no_quality": "quality_report.csv пока не найден.",
        "no_sentiment": "Нет результатов анализа тональности. Запустите predict-sentiment.",
        "no_map": "Координаты не найдены или пустые. Для карты нужны latitude/longitude либо lat/lon.",
        "empty_after_filters": "После применения фильтров данных не осталось.",
        "search": "Поиск по тексту отзыва или названию объекта",
        "reset_hint": "Чтобы вернуть все данные, очистите выбранные фильтры.",
        "download": "Скачать отфильтрованные данные CSV",
        "method_title": "Методическая логика панели",
        "method_text": "Панель отражает поток данных дипломного проекта: сбор отзывов, очистка и нормализация, контроль качества, сохранение и визуализация аналитических показателей.",
    },
    "kk": {
        "title": "Туристік нысандар пікірлерін талдау және визуализациялау жүйесі",
        "caption": "Тазартылған, нормаланған және дайындалған пайдаланушы пікірлері негізінде туристік нысандарды бағалауға арналған интерактивті панель.",
        "badge": "Дипломдық жоба",
        "filters": "Сүзгілер",
        "city": "Қала",
        "type": "Нысан түрі",
        "source": "Дереккөз",
        "language": "Тіл",
        "quality_status": "Деректер сапасының мәртебесі",
        "sentiment": "Тоналдылық",
        "objects": "Нысандар",
        "reviews": "Пікірлер",
        "avg_rating": "Орташа рейтинг",
        "valid_share": "Жарамды үлесі",
        "duplicates": "Анықталған дубликаттар",
        "data_source": "Деректер көзі",
        "source_postgres": "PostgreSQL",
        "source_csv": "CSV demo fallback",
        "postgres_warning": "PostgreSQL дерекқорынан оқу мүмкін болмады, CSV fallback қолданылады. Себебі:",
        "no_data": "Көрсету үшін деректер жоқ. Іске қосыңыз: python -m src.main run-sample-pipeline",
        "overview": "Шолу",
        "analytics": "Талдау",
        "quality": "Деректер сапасы",
        "reviews_table": "Пікірлер",
        "map": "Карта",
        "rating_distribution": "Рейтингтердің таралуы",
        "rating_distribution_title": "Нормаланған бағалардың таралуы",
        "rating_normalized": "Нормаланған баға",
        "review_count": "Пікірлер саны",
        "language_distribution": "Тілдердің таралуы",
        "language_distribution_title": "Пікір тілдері",
        "sentiment_distribution": "Тоналдылықтың таралуы",
        "sentiment_distribution_title": "Пікірлер тоналдылығы",
        "type_distribution": "Нысан түрлері бойынша таралу",
        "city_distribution": "Қалалар бойынша таралу",
        "source_distribution": "Дереккөздер бойынша таралу",
        "quality_distribution": "Сапа мәртебелері бойынша таралу",
        "top_objects": "Пікір саны бойынша үздік нысандар",
        "object_name": "Нысан атауы",
        "no_quality": "quality_report.csv файлы әзірге табылған жоқ.",
        "no_sentiment": "Тоналдылықты талдау нәтижелері жоқ. predict-sentiment іске қосыңыз.",
        "no_map": "Координаттар табылмады немесе бос. Карта үшін latitude/longitude немесе lat/lon қажет.",
        "empty_after_filters": "Сүзгілерден кейін деректер қалмады.",
        "search": "Пікір мәтіні немесе нысан атауы бойынша іздеу",
        "reset_hint": "Барлық деректерді қайтару үшін таңдалған сүзгілерді тазалаңыз.",
        "download": "Сүзілген деректерді CSV ретінде жүктеу",
        "method_title": "Панельдің әдістемелік логикасы",
        "method_text": "Панель дипломдық жобаның деректер ағынын көрсетеді: пікірлерді жинау, тазарту және нормалау, сапаны бақылау, сақтау және аналитикалық көрсеткіштерді визуализациялау.",
    },
}

LABELS = {
    "ru": {
        "columns_quality": {"metric": "Показатель", "formula": "Формула", "numerator": "Числитель", "denominator": "Знаменатель", "value": "Значение"},
        "columns_reviews": {
            "city": "Город", "type": "Тип объекта", "name": "Название объекта", "source": "Источник",
            "author": "Автор", "text_cleaned": "Очищенный текст отзыва", "review_text": "Текст отзыва",
            "rating": "Исходная оценка", "rating_normalized": "Нормализованная оценка",
            "review_date": "Дата отзыва", "language": "Язык", "quality_status": "Статус качества",
            "sentiment_label": "Тональность", "sentiment_score": "Оценка тональности",
        },
        "type": {"museum": "Музей", "hotel": "Отель", "attraction": "Достопримечательность", "restaurant": "Ресторан", "recreation": "Зона отдыха", "cultural_object": "Культурный объект"},
        "quality_status": {"valid": "Пригоден", "limited": "Ограниченно пригоден", "rejected": "Отклонён", "unknown": "Не определён"},
        "sentiment": {"positive": "Положительная", "neutral": "Нейтральная", "negative": "Отрицательная", "unknown": "Не определена"},
        "language": {"ru": "Русский", "kk": "Казахский", "mixed": "Смешанный", "unknown": "Не определён"},
        "source": {"yandex_maps": "Yandex Maps", "google_maps": "Google Maps", "2gis": "2GIS", "unknown": "Не определён"},
        "quality_metric": {"K_tolyqtyk": "Коэффициент полноты", "K_tolyktyk": "Коэффициент полноты", "K_dubl": "Доля дубликатов", "K_zharamdy": "Доля пригодных записей", "K_unknown": "Доля неопределённого языка"},
        "quality_formula": {"N_tolyq / N_zhalpy": "N_полных / N_общих", "N_tolyk / N_zhalpy": "N_полных / N_общих", "N_dubl / N_zhalpy": "N_дубликатов / N_общих", "N_korpus / N_zhinalgan": "N_корпус / N_собранных", "N_unknown / N_zhalpy": "N_unknown / N_общих"},
    },
    "kk": {
        "columns_quality": {"metric": "Көрсеткіш", "formula": "Формула", "numerator": "Алым", "denominator": "Бөлім", "value": "Мәні"},
        "columns_reviews": {
            "city": "Қала", "type": "Нысан түрі", "name": "Нысан атауы", "source": "Дереккөз",
            "author": "Автор", "text_cleaned": "Тазартылған пікір мәтіні", "review_text": "Пікір мәтіні",
            "rating": "Бастапқы баға", "rating_normalized": "Нормаланған баға",
            "review_date": "Пікір күні", "language": "Тіл", "quality_status": "Сапа мәртебесі",
            "sentiment_label": "Тоналдылық", "sentiment_score": "Тоналдылық бағасы",
        },
        "type": {"museum": "Музей", "hotel": "Қонақүй", "attraction": "Көрікті орын", "restaurant": "Мейрамхана", "recreation": "Демалыс аймағы", "cultural_object": "Мәдени нысан"},
        "quality_status": {"valid": "Жарамды", "limited": "Шектеулі жарамды", "rejected": "Қабылданбаған", "unknown": "Анықталмаған"},
        "sentiment": {"positive": "Оң", "neutral": "Бейтарап", "negative": "Теріс", "unknown": "Анықталмаған"},
        "language": {"ru": "Орыс тілі", "kk": "Қазақ тілі", "mixed": "Аралас", "unknown": "Анықталмаған"},
        "source": {"yandex_maps": "Yandex Maps", "google_maps": "Google Maps", "2gis": "2GIS", "unknown": "Анықталмаған"},
        "quality_metric": {"K_tolyqtyk": "Толықтық коэффициенті", "K_tolyktyk": "Толықтық коэффициенті", "K_dubl": "Қайталанатын жазбалар үлесі", "K_zharamdy": "Жарамды жазбалар үлесі", "K_unknown": "Тілі анықталмаған жазбалар үлесі"},
        "quality_formula": {"N_tolyq / N_zhalpy": "N_толық / N_жалпы", "N_tolyk / N_zhalpy": "N_толық / N_жалпы", "N_dubl / N_zhalpy": "N_дубликат / N_жалпы", "N_korpus / N_zhinalgan": "N_корпус / N_жиналған", "N_unknown / N_zhalpy": "N_unknown / N_жалпы"},
    },
}


def inject_css() -> None:
    st.markdown("""
    <style>
    :root {
        --bg:#f4f7fb; --card:#fff; --text:#0f172a; --muted:#64748b;
        --line:#e5e7eb; --primary:#0f766e; --shadow:0 14px 34px rgba(15,23,42,.08);
    }
    .stApp {
        background: radial-gradient(circle at 5% 0%, rgba(37,99,235,.12), transparent 30%),
                    radial-gradient(circle at 95% 8%, rgba(15,118,110,.13), transparent 28%),
                    linear-gradient(180deg,#f8fafc 0%,var(--bg) 100%);
    }
    .block-container {padding-top:2rem; padding-bottom:2.5rem; max-width:1400px;}
    section[data-testid="stSidebar"] {background:rgba(255,255,255,.94); border-right:1px solid var(--line);}
    .hero {
        display:flex; justify-content:space-between; align-items:center; gap:24px;
        padding:30px 34px; margin-bottom:24px; border-radius:28px;
        background:linear-gradient(135deg,rgba(15,118,110,.96),rgba(37,99,235,.96));
        color:white; box-shadow:0 22px 50px rgba(15,118,110,.22); overflow:hidden; position:relative;
    }
    .hero:after {content:""; position:absolute; right:-80px; top:-80px; width:230px; height:230px; border-radius:999px; background:rgba(255,255,255,.12);}
    .hero h1 {font-size:34px; line-height:1.22; margin:0 0 10px 0; font-weight:850; letter-spacing:-.02em; max-width:980px;}
    .hero p {margin:0; font-size:16px; opacity:.94; max-width:940px;}
    .hero-badge {z-index:1; padding:10px 15px; border-radius:999px; background:rgba(255,255,255,.16); border:1px solid rgba(255,255,255,.30); font-weight:750; white-space:nowrap; font-size:14px;}
    .metric-card, .info-card, .chart-card {
        border-radius:22px; background:rgba(255,255,255,.96); border:1px solid var(--line); box-shadow:var(--shadow);
    }
    .metric-card {padding:19px 20px; min-height:118px;}
    .metric-title {display:flex; gap:8px; color:var(--muted); font-size:14px; font-weight:700; margin-bottom:10px;}
    .metric-value {color:var(--text); font-size:31px; font-weight:850; letter-spacing:-.03em;}
    .metric-help {color:var(--muted); font-size:12px; margin-top:8px;}
    .info-card {padding:20px 22px; margin-bottom:20px;}
    .info-card h3 {margin:0 0 8px 0; color:var(--text); font-size:18px;}
    .info-card p {margin:0; color:var(--muted); line-height:1.58; font-size:14px;}
    .chart-card {padding:18px 18px 10px 18px; margin-bottom:20px;}
    .small-label {display:inline-flex; padding:7px 11px; border-radius:999px; background:#ecfdf5; color:#047857; border:1px solid #bbf7d0; font-size:12px; font-weight:800; margin-bottom:12px;}
    div[data-testid="stDataFrame"] {border-radius:18px; overflow:hidden; border:1px solid var(--line);}
    .stTabs [data-baseweb="tab-list"] {gap:10px; background:rgba(255,255,255,.58); padding:8px; border-radius:999px; border:1px solid var(--line); width:fit-content;}
    .stTabs [data-baseweb="tab"] {padding:9px 17px; border-radius:999px; font-weight:750;}
    .stTabs [aria-selected="true"] {background:#0f766e!important; color:white!important;}
    h1,h2,h3 {color:var(--text);}
    .stDownloadButton button {border-radius:999px; font-weight:750;}
    @media (max-width:900px) {.hero{flex-direction:column;align-items:flex-start}.hero h1{font-size:27px}}
    </style>
    """, unsafe_allow_html=True)


def get_database_url() -> str | None:
    try:
        if "DATABASE_URL" in st.secrets:
            return st.secrets["DATABASE_URL"]
        if "postgres" in st.secrets:
            cfg = st.secrets["postgres"]
            user = cfg["user"]
            password = quote_plus(cfg["password"])
            host = cfg["host"]
            port = cfg.get("port", 5432)
            database = cfg["database"]
            sslmode = cfg.get("sslmode", "require")
            return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}?sslmode={sslmode}"
    except Exception:
        pass
    return os.getenv("DATABASE_URL")


def _find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    lowered = {str(col).strip().lower(): col for col in df.columns}
    for candidate in candidates:
        key = candidate.strip().lower()
        if key in lowered:
            return lowered[key]
    return None


def standardize_coordinates(df: pd.DataFrame) -> pd.DataFrame:
    """Создаёт стандартные поля latitude/longitude из разных вариантов названий."""
    df = df.copy()
    latitude_aliases = [
        "latitude", "lat", "y", "geo_lat", "coord_lat", "coords_lat",
        "object_latitude", "latitude_object", "lat_object", "широта",
    ]
    longitude_aliases = [
        "longitude", "lon", "lng", "long", "x", "geo_lon", "geo_lng",
        "coord_lon", "coord_lng", "coords_lon", "coords_lng",
        "object_longitude", "longitude_object", "lon_object", "lng_object", "долгота",
    ]

    lat_col = _find_column(df, latitude_aliases)
    lon_col = _find_column(df, longitude_aliases)

    if lat_col is not None and "latitude" not in df.columns:
        df["latitude"] = df[lat_col]
    if lon_col is not None and "longitude" not in df.columns:
        df["longitude"] = df[lon_col]

    for col in ["latitude", "longitude"]:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(",", ".", regex=False)
                .str.extract(r"([-+]?\d+(?:\.\d+)?)", expand=False)
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def normalize_source_value(value: object) -> str:
    """Приводит разные названия одного источника к единому виду.

    Например, yandex и yandex_maps считаются одним источником: yandex_maps.
    Это нужно, чтобы в фильтре и диаграммах не появлялись два одинаковых источника.
    """
    if pd.isna(value):
        return "unknown"

    source = str(value).strip().lower()
    source = source.replace("-", "_").replace(" ", "_")

    source_aliases = {
        "yandex": "yandex_maps",
        "yandex_map": "yandex_maps",
        "yandex_maps": "yandex_maps",
        "яндекс": "yandex_maps",
        "яндекс_карты": "yandex_maps",
        "yandex_karty": "yandex_maps",

        "google": "google_maps",
        "google_map": "google_maps",
        "google_maps": "google_maps",
        "googlemaps": "google_maps",
        "гугл": "google_maps",
        "гугл_карты": "google_maps",

        "2gis": "2gis",
        "2_gis": "2gis",
        "doublegis": "2gis",
        "двугис": "2gis",
    }

    return source_aliases.get(source, source or "unknown")


def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = standardize_coordinates(df)
    for col in ["city", "type", "source", "language", "quality_status", "sentiment_label"]:
        if col not in df.columns:
            df[col] = "unknown"
        df[col] = df[col].fillna("unknown").astype(str)

    # Нормализация источников: yandex и yandex_maps объединяются в один источник.
    df["source"] = df["source"].apply(normalize_source_value)

    if "name" not in df.columns:
        df["name"] = "unknown"

    for col in ["rating", "rating_normalized", "sentiment_score", "latitude", "longitude"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "review_date" in df.columns:
        df["review_date"] = pd.to_datetime(df["review_date"], errors="coerce")

    if "text_cleaned" not in df.columns and "review_text" in df.columns:
        df["text_cleaned"] = df["review_text"]

    return df


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
    objects = pd.read_csv(OBJECTS_PROCESSED_CSV) if OBJECTS_PROCESSED_CSV.exists() else pd.DataFrame()
    sentiment = pd.read_csv(SENTIMENT_PREDICTIONS_CSV) if SENTIMENT_PREDICTIONS_CSV.exists() else pd.DataFrame()
    df = reviews.copy()
    if not objects.empty:
        objects = standardize_coordinates(objects)

    if not objects.empty:
        object_cols = [c for c in ["id", "source_object_id", "name", "type", "city", "latitude", "longitude", "source_url"] if c in objects.columns]
        if "source_object_id" in df.columns and "source_object_id" in objects.columns:
            df = df.merge(objects[object_cols].drop_duplicates("source_object_id"), on="source_object_id", how="left", suffixes=("", "_object"))
        elif "object_id" in df.columns and "id" in objects.columns:
            obj = objects[object_cols].rename(columns={"id": "object_id"})
            df = df.merge(obj.drop_duplicates("object_id"), on="object_id", how="left", suffixes=("", "_object"))

    if not sentiment.empty and "review_id" in sentiment.columns and "review_id" in df.columns:
        sent_cols = [c for c in ["review_id", "sentiment_label", "sentiment_score"] if c in sentiment.columns]
        df = df.merge(sentiment[sent_cols].drop_duplicates("review_id"), on="review_id", how="left", suffixes=("", "_pred"))
        if "sentiment_label_pred" in df.columns:
            df["sentiment_label"] = df.get("sentiment_label", pd.Series(index=df.index, dtype="object")).fillna(df["sentiment_label_pred"])
            df = df.drop(columns=["sentiment_label_pred"])
        if "sentiment_score_pred" in df.columns:
            df["sentiment_score"] = df.get("sentiment_score", pd.Series(index=df.index, dtype="float")).fillna(df["sentiment_score_pred"])
            df = df.drop(columns=["sentiment_score_pred"])

    return prepare_dataframe(df), load_quality_report()


@st.cache_data(show_spinner=False)
def load_from_db(database_url: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    engine = create_engine(database_url, pool_pre_ping=True)

    sql_with_analysis = text("""
        WITH latest_analysis AS (
            SELECT DISTINCT ON (review_id)
                review_id,
                sentiment_label,
                sentiment_score,
                model_name,
                feature_method,
                predicted_at
            FROM review_analysis
            ORDER BY review_id, predicted_at DESC NULLS LAST, id DESC
        )
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
            a.sentiment_label AS sentiment_label,
            a.sentiment_score AS sentiment_score
        FROM reviews r
        JOIN tourist_objects o ON o.id = r.object_id
        LEFT JOIN latest_analysis a ON a.review_id = r.id
    """)

    sql_without_analysis = text("""
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
            NULL::text AS sentiment_label,
            NULL::numeric AS sentiment_score
        FROM reviews r
        JOIN tourist_objects o ON o.id = r.object_id
    """)

    with engine.connect() as conn:
        try:
            df = pd.read_sql_query(sql_with_analysis, conn)
        except Exception:
            df = pd.read_sql_query(sql_without_analysis, conn)

    return prepare_dataframe(df), load_quality_report()


def metric_card(title: str, value: str, icon: str, help_text: str = "") -> None:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title"><span>{escape(icon)}</span><span>{escape(title)}</span></div>
        <div class="metric-value">{escape(value)}</div>
        <div class="metric-help">{escape(help_text)}</div>
    </div>
    """, unsafe_allow_html=True)


def info_card(title: str, text_value: str) -> None:
    st.markdown(f"""
    <div class="info-card">
        <h3>{escape(title)}</h3>
        <p>{escape(text_value)}</p>
    </div>
    """, unsafe_allow_html=True)


def chart_start(label: str) -> None:
    st.markdown(f'<div class="chart-card"><div class="small-label">{escape(label)}</div>', unsafe_allow_html=True)


def chart_end() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def style_chart(fig, height: int = 430):
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=40, r=45, t=70, b=50),
        title=dict(x=0.02, xanchor="left", font=dict(size=18)),
        font=dict(size=13),
        legend=dict(orientation="h", yanchor="bottom", y=-0.28, xanchor="center", x=0.5),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(15,23,42,.08)")
    return fig


def style_donut_chart(fig, height: int = 430):
    fig.update_traces(
        textposition="inside",
        textinfo="percent",
        insidetextorientation="horizontal",
        textfont_size=14,
        marker=dict(line=dict(color="white", width=2)),
        hovertemplate="%{label}<br>%{value} записей<br>%{percent}<extra></extra>",
    )
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=20, r=20, t=70, b=70),
        title=dict(x=0.02, xanchor="left", font=dict(size=18)),
        font=dict(size=13),
        legend=dict(orientation="h", yanchor="bottom", y=-0.18, xanchor="center", x=0.5),
        uniformtext_minsize=12,
        uniformtext_mode="hide",
    )
    return fig


def format_percent(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "—"
    if abs(value) < 0.0005:
        return "0%"
    return f"{value:.1%}"


def to_bool_series(series: pd.Series) -> pd.Series:
    return (
        series
        .fillna(False)
        .astype(str)
        .str.lower()
        .map({
            "true": True,
            "1": True,
            "yes": True,
            "y": True,
            "да": True,
            "false": False,
            "0": False,
            "no": False,
            "n": False,
            "нет": False,
            "nan": False,
            "none": False,
            "": False,
        })
        .fillna(False)
        .astype(bool)
    )


def translate_values(df: pd.DataFrame, column: str, labels: dict[str, str]) -> pd.DataFrame:
    if column in df.columns:
        df[column] = df[column].fillna("unknown").astype(str).replace(labels)
    return df


def multiselect_filter(df: pd.DataFrame, column: str, label: str, value_labels: dict[str, str] | None = None) -> pd.DataFrame:
    if column not in df.columns or df[column].dropna().empty:
        return df
    value_labels = value_labels or {}
    values = sorted(df[column].dropna().astype(str).unique())
    selected = st.sidebar.multiselect(
        label,
        options=values,
        default=values,
        format_func=lambda x: value_labels.get(str(x), str(x)),
    )
    return df[df[column].astype(str).isin(selected)] if selected else df


def search_filter(df: pd.DataFrame, query: str) -> pd.DataFrame:
    query = query.lower().strip()
    if not query:
        return df
    search_columns = [c for c in ["name", "text_cleaned", "review_text", "author"] if c in df.columns]
    mask = pd.Series(False, index=df.index)
    for column in search_columns:
        mask = mask | df[column].fillna("").astype(str).str.lower().str.contains(query, regex=False)
    return df[mask]


def make_counts(df: pd.DataFrame, column: str, name_col: str, count_col: str, labels: dict[str, str] | None = None) -> pd.DataFrame:
    if column not in df.columns:
        return pd.DataFrame(columns=[name_col, count_col])
    counts = df[column].fillna("unknown").astype(str).replace(labels or {}).value_counts().reset_index()
    counts.columns = [name_col, count_col]
    return counts


def csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")


def main() -> None:
    inject_css()

    interface_lang = st.sidebar.radio(
        "Интерфейс / Тіл",
        options=["ru", "kk"],
        format_func=lambda x: "Русский" if x == "ru" else "Қазақша",
        horizontal=True,
    )
    T = UI[interface_lang]
    L = LABELS[interface_lang]

    st.markdown(f"""
    <div class="hero">
        <div>
            <h1>{escape(T["title"])}</h1>
            <p>{escape(T["caption"])}</p>
        </div>
        <div class="hero-badge">{escape(T["badge"])}</div>
    </div>
    """, unsafe_allow_html=True)

    database_url = get_database_url()
    data_source = T["source_csv"]

    try:
        if database_url:
            df, quality = load_from_db(database_url)
            data_source = T["source_postgres"]
        else:
            df, quality = load_from_csv()
            data_source = T["source_csv"]
    except Exception as exc:
        st.warning(f"{T['postgres_warning']} {exc}")
        df, quality = load_from_csv()
        data_source = T["source_csv"]

    if df.empty:
        st.error(T["no_data"])
        return

    st.sidebar.header(T["filters"])
    filtered = df.copy()
    filtered = multiselect_filter(filtered, "city", T["city"])
    filtered = multiselect_filter(filtered, "type", T["type"], L["type"])
    filtered = multiselect_filter(filtered, "source", T["source"], L["source"])
    filtered = multiselect_filter(filtered, "language", T["language"], L["language"])
    filtered = multiselect_filter(filtered, "quality_status", T["quality_status"], L["quality_status"])
    filtered = multiselect_filter(filtered, "sentiment_label", T["sentiment"], L["sentiment"])
    filtered = search_filter(filtered, st.sidebar.text_input(T["search"], value=""))
    st.sidebar.caption(T["reset_hint"])

    if filtered.empty:
        st.warning(T["empty_after_filters"])
        return

    # quality_df — выбранная пользователем выборка ДО исключения дубликатов.
    # По ней считаются показатели качества, чтобы показать, сколько проблем было найдено.
    quality_df = filtered.copy()

    if "is_duplicate" in quality_df.columns:
        duplicate_mask = to_bool_series(quality_df["is_duplicate"])
        duplicate_share = duplicate_mask.mean()
        analysis_df = quality_df.loc[~duplicate_mask].copy()
    else:
        duplicate_share = None
        analysis_df = quality_df.copy()

    # analysis_df — корпус для аналитики и визуализации ПОСЛЕ исключения дубликатов.
    # Поэтому графики, таблица отзывов и карта не искажаются повторяющимися записями.
    if analysis_df.empty:
        st.warning(T["empty_after_filters"])
        return

    if "source_object_id" in analysis_df.columns:
        object_count = int(analysis_df["source_object_id"].nunique())
    elif "object_id" in analysis_df.columns:
        object_count = int(analysis_df["object_id"].nunique())
    else:
        object_count = int(analysis_df["name"].nunique()) if "name" in analysis_df.columns else 0

    review_count = len(analysis_df)
    avg_rating = analysis_df["rating_normalized"].mean() if "rating_normalized" in analysis_df.columns else None
    valid_share = (quality_df["quality_status"].astype(str) == "valid").mean() if "quality_status" in quality_df.columns else None

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        metric_card(T["objects"], f"{object_count:,}".replace(",", " "), "🏛️", T["object_name"])
    with c2:
        metric_card(T["reviews"], f"{review_count:,}".replace(",", " "), "📝", T["review_count"])
    with c3:
        metric_card(T["avg_rating"], f"{avg_rating:.2f}" if pd.notna(avg_rating) else "—", "⭐", T["rating_normalized"])
    with c4:
        metric_card(T["valid_share"], format_percent(valid_share), "✅", T["quality_status"])
    with c5:
        metric_card(T["duplicates"], format_percent(duplicate_share), "♻️", "До исключения из анализа" if interface_lang == "ru" else "Талдаудан шығару алдында")

    st.markdown("")

    tab_overview, tab_analytics, tab_quality, tab_reviews, tab_map = st.tabs([
        f"📌 {T['overview']}",
        f"📊 {T['analytics']}",
        f"✅ {T['quality']}",
        f"📝 {T['reviews_table']}",
        f"🗺️ {T['map']}",
    ])

    with tab_overview:
        left, right = st.columns([1.2, 1])
        with left:
            info_card(T["method_title"], T["method_text"])
        with right:
            info_card(T["data_source"], data_source)

        col_a, col_b = st.columns(2)

        with col_a:
            chart_start(T["city_distribution"])
            city_counts = make_counts(analysis_df, "city", T["city"], T["review_count"])
            if not city_counts.empty:
                fig = px.bar(city_counts.head(12), x=T["review_count"], y=T["city"], orientation="h", title=T["city_distribution"], text=T["review_count"])
                fig.update_traces(textposition="outside", cliponaxis=False)
                fig.update_yaxes(autorange="reversed")
                st.plotly_chart(style_chart(fig), use_container_width=True)
            chart_end()

        with col_b:
            chart_start(T["top_objects"])
            if "name" in analysis_df.columns:
                obj_counts = analysis_df["name"].fillna("unknown").astype(str).value_counts().head(12).reset_index()
                obj_counts.columns = [T["object_name"], T["review_count"]]
                fig = px.bar(obj_counts, x=T["review_count"], y=T["object_name"], orientation="h", title=T["top_objects"], text=T["review_count"])
                fig.update_traces(textposition="outside", cliponaxis=False)
                fig.update_yaxes(autorange="reversed")
                st.plotly_chart(style_chart(fig), use_container_width=True)
            chart_end()

    with tab_analytics:
        chart_start(T["rating_distribution"])
        if "rating_normalized" in analysis_df.columns:
            rating_df = analysis_df[analysis_df["rating_normalized"].notna()].copy()
            rating_df["rating_group"] = rating_df["rating_normalized"].round(2)
            rating_counts = rating_df["rating_group"].value_counts().sort_index().reset_index()
            rating_counts.columns = [T["rating_normalized"], T["review_count"]]
            if not rating_counts.empty:
                fig = px.bar(rating_counts, x=T["rating_normalized"], y=T["review_count"], title=T["rating_distribution_title"], text=T["review_count"])
                fig.update_traces(textposition="outside", cliponaxis=False, marker_line_width=1, marker_line_color="white", opacity=.94)
                fig.update_xaxes(title_text=T["rating_normalized"], type="category")
                max_count = rating_counts[T["review_count"]].max()
                fig.update_yaxes(title_text=T["review_count"], range=[0, max_count * 1.16 if max_count > 0 else 1])
                st.plotly_chart(style_chart(fig), use_container_width=True)
        chart_end()

        col_a, col_b = st.columns(2)

        with col_a:
            chart_start(T["language_distribution"])
            language_counts = make_counts(analysis_df, "language", T["language"], T["review_count"], L["language"])
            if not language_counts.empty:
                fig = px.pie(language_counts, names=T["language"], values=T["review_count"], title=T["language_distribution_title"], hole=.48)
                st.plotly_chart(style_donut_chart(fig), use_container_width=True)
            chart_end()

        with col_b:
            chart_start(T["sentiment_distribution"])
            if "sentiment_label" in analysis_df.columns and analysis_df["sentiment_label"].notna().any():
                sentiment_counts = make_counts(analysis_df, "sentiment_label", T["sentiment"], T["review_count"], L["sentiment"])
                fig = px.bar(sentiment_counts, x=T["review_count"], y=T["sentiment"], orientation="h", title=T["sentiment_distribution_title"], text=T["review_count"])
                fig.update_traces(textposition="outside", cliponaxis=False, marker_line_width=1, marker_line_color="white", opacity=.94)
                fig.update_yaxes(autorange="reversed")
                st.plotly_chart(style_chart(fig), use_container_width=True)
            else:
                st.info(T["no_sentiment"])
            chart_end()

        col_c, col_d = st.columns(2)

        with col_c:
            chart_start(T["type_distribution"])
            type_counts = make_counts(analysis_df, "type", T["type"], T["review_count"], L["type"])
            if not type_counts.empty:
                fig = px.bar(type_counts, x=T["type"], y=T["review_count"], title=T["type_distribution"], text=T["review_count"])
                fig.update_traces(textposition="outside", cliponaxis=False, marker_line_width=1, marker_line_color="white", opacity=.94)
                st.plotly_chart(style_chart(fig), use_container_width=True)
            chart_end()

        with col_d:
            chart_start(T["source_distribution"])
            source_counts = make_counts(analysis_df, "source", T["source"], T["review_count"], L["source"])
            if not source_counts.empty:
                fig = px.pie(source_counts, names=T["source"], values=T["review_count"], title=T["source_distribution"], hole=.52)
                st.plotly_chart(style_donut_chart(fig), use_container_width=True)
            chart_end()

    with tab_quality:
        total_quality = len(quality_df)

        valid_count = int((quality_df["quality_status"].astype(
            str) == "valid").sum()) if "quality_status" in quality_df.columns else 0
        limited_count = int((quality_df["quality_status"].astype(
            str) == "limited").sum()) if "quality_status" in quality_df.columns else 0
        rejected_count = int((quality_df["quality_status"].astype(
            str) == "rejected").sum()) if "quality_status" in quality_df.columns else 0

        valid_percent = valid_count / total_quality if total_quality else None
        limited_percent = limited_count / total_quality if total_quality else None
        rejected_percent = rejected_count / total_quality if total_quality else None

        q1, q2, q3, q4 = st.columns(4)

        with q1:
            metric_card(
                "Жарамды / Пригодные",
                f"{valid_count}",
                "✅",
                format_percent(valid_percent),
            )

        with q2:
            metric_card(
                "Шектеулі / Ограниченные",
                f"{limited_count}",
                "⚠️",
                format_percent(limited_percent),
            )

        with q3:
            metric_card(
                "Қабылданбаған / Отклонённые",
                f"{rejected_count}",
                "⛔",
                format_percent(rejected_percent),
            )

        with q4:
            metric_card(
                T["duplicates"],
                format_percent(duplicate_share),
                "♻️",
                "До исключения из анализа" if interface_lang == "ru" else "Талдаудан шығару алдында",
            )

        st.markdown("")

        col_a, col_b = st.columns([1.1, 1])

        with col_a:
            chart_start(T["quality_distribution"])

            quality_counts = make_counts(
                quality_df,
                "quality_status",
                T["quality_status"],
                T["review_count"],
                L["quality_status"],
            )

            if not quality_counts.empty:
                fig = px.bar(
                    quality_counts,
                    x=T["quality_status"],
                    y=T["review_count"],
                    title=T["quality_distribution"],
                    text=T["review_count"],
                )

                fig.update_traces(
                    textposition="outside",
                    cliponaxis=False,
                    marker_line_width=1,
                    marker_line_color="white",
                    opacity=.94,
                )

                st.plotly_chart(style_chart(fig), use_container_width=True)

            chart_end()

        with col_b:
            if not quality.empty:
                quality_display = quality.copy()

                if "metric" in quality_display.columns:
                    quality_display["metric"] = (
                        quality_display["metric"]
                        .astype(str)
                        .replace(L["quality_metric"])
                    )

                if "formula" in quality_display.columns:
                    quality_display["formula"] = (
                        quality_display["formula"]
                        .astype(str)
                        .replace(L["quality_formula"])
                    )

                quality_display = quality_display.rename(columns=L["columns_quality"])

                st.dataframe(
                    quality_display,
                    use_container_width=True,
                    height=360,
                )
            else:
                st.info(T["no_quality"])

        with st.expander("ℹ️ Түсіндірме / Пояснение показателей"):
            st.markdown(
                """
                **Valid / Жарамды** — отзыв пригоден для аналитического корпуса.

                **Limited / Шектеулі** — отзыв можно использовать ограниченно, например при неполных данных.

                **Rejected / Қабылданбаған** — отзыв исключается из основного анализа.

                **Дубликаты** рассчитываются до исключения повторяющихся записей из аналитического корпуса. 
                Это показывает, сколько повторов было обнаружено на этапе контроля качества данных.
                """
            )

    with tab_reviews:
        columns = [
            "city", "type", "name", "source", "author", "text_cleaned", "review_text",
            "rating", "rating_normalized", "review_date", "language",
            "quality_status", "sentiment_label", "sentiment_score",
        ]
        columns = [c for c in columns if c in analysis_df.columns]
        reviews_display = analysis_df[columns].copy()
        reviews_display = translate_values(reviews_display, "type", L["type"])
        reviews_display = translate_values(reviews_display, "source", L["source"])
        reviews_display = translate_values(reviews_display, "quality_status", L["quality_status"])
        reviews_display = translate_values(reviews_display, "sentiment_label", L["sentiment"])
        reviews_display = translate_values(reviews_display, "language", L["language"])

        if "review_date" in reviews_display.columns:
            reviews_display["review_date"] = reviews_display["review_date"].astype(str).replace("NaT", "")

        reviews_display = reviews_display.rename(columns=L["columns_reviews"])

        st.download_button(
            label=T["download"],
            data=csv_bytes(reviews_display),
            file_name="analysis_tourist_reviews.csv",
            mime="text/csv",
        )
        st.dataframe(reviews_display, use_container_width=True, height=560)

    with tab_map:
        map_source = standardize_coordinates(analysis_df)
        if {"latitude", "longitude"}.issubset(map_source.columns):
            map_df = map_source.dropna(subset=["latitude", "longitude"]).copy()
            map_df = map_df.drop_duplicates(subset=["name", "latitude", "longitude"])
            if not map_df.empty:
                st.map(map_df, latitude="latitude", longitude="longitude", size=24)
                map_cols = [c for c in ["city", "type", "name", "latitude", "longitude", "rating_normalized"] if c in map_df.columns]
                map_display = map_df[map_cols].drop_duplicates().copy()
                map_display = translate_values(map_display, "type", L["type"])
                map_display = map_display.rename(columns=L["columns_reviews"])
                st.dataframe(map_display, use_container_width=True, height=320)
            else:
                st.info(T["no_map"])
        else:
            st.info(T["no_map"])


if __name__ == "__main__":
    main()
