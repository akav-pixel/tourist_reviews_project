-- PostgreSQL schema for tourist_reviews_project
-- Дипломный проект: анализ и визуализация пользовательских отзывов о туристических объектах.

CREATE TABLE IF NOT EXISTS canonical_objects (
    canonical_object_id BIGSERIAL PRIMARY KEY,
    canonical_name VARCHAR(500) NOT NULL,
    object_type VARCHAR(100),
    city VARCHAR(150),
    latitude NUMERIC(10, 7),
    longitude NUMERIC(10, 7),
    normalized_name VARCHAR(500),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_canonical_object UNIQUE (normalized_name, city, object_type)
);

CREATE TABLE IF NOT EXISTS parse_runs (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(100) NOT NULL,
    city VARCHAR(150),
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP,
    status VARCHAR(50) NOT NULL DEFAULT 'started',
    objects_count INTEGER NOT NULL DEFAULT 0,
    reviews_count INTEGER NOT NULL DEFAULT 0,
    rejected_count INTEGER NOT NULL DEFAULT 0,
    raw_path TEXT,
    log_path TEXT,
    CONSTRAINT chk_parse_run_status CHECK (status IN ('started', 'finished', 'failed', 'partial'))
);

CREATE TABLE IF NOT EXISTS tourist_objects (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(500) NOT NULL,
    type VARCHAR(100),
    city VARCHAR(150),
    source VARCHAR(100) NOT NULL,
    source_object_id VARCHAR(255),
    source_url TEXT,
    latitude NUMERIC(10, 7),
    longitude NUMERIC(10, 7),
    canonical_object_id BIGINT REFERENCES canonical_objects(canonical_object_id) ON DELETE SET NULL,
    normalized_name VARCHAR(500),
    loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    parse_run_id BIGINT REFERENCES parse_runs(id) ON DELETE SET NULL,
    raw_ref TEXT,
    CONSTRAINT uq_source_object UNIQUE (source, source_object_id)
);

CREATE INDEX IF NOT EXISTS idx_tourist_objects_city ON tourist_objects(city);
CREATE INDEX IF NOT EXISTS idx_tourist_objects_type ON tourist_objects(type);
CREATE INDEX IF NOT EXISTS idx_tourist_objects_source ON tourist_objects(source);

CREATE TABLE IF NOT EXISTS reviews (
    id BIGSERIAL PRIMARY KEY,
    object_id BIGINT NOT NULL REFERENCES tourist_objects(id) ON DELETE CASCADE,
    source VARCHAR(100) NOT NULL,
    review_id VARCHAR(255),
    author TEXT,
    review_text TEXT,
    text_cleaned TEXT,
    rating NUMERIC(4, 2),
    rating_normalized NUMERIC(4, 2),
    review_date DATE,
    language VARCHAR(20) NOT NULL DEFAULT 'unknown',
    url TEXT,
    loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    quality_status VARCHAR(20) NOT NULL DEFAULT 'limited',
    is_duplicate BOOLEAN NOT NULL DEFAULT FALSE,
    raw_ref TEXT,
    parse_run_id BIGINT REFERENCES parse_runs(id) ON DELETE SET NULL,
    CONSTRAINT chk_language CHECK (language IN ('ru', 'kk', 'mixed', 'unknown')),
    CONSTRAINT chk_quality_status CHECK (quality_status IN ('valid', 'limited', 'rejected')),
    CONSTRAINT chk_rating_normalized CHECK (rating_normalized IS NULL OR (rating_normalized >= 0 AND rating_normalized <= 5)),
    CONSTRAINT uq_source_review UNIQUE (source, review_id)
);

CREATE INDEX IF NOT EXISTS idx_reviews_object_id ON reviews(object_id);
CREATE INDEX IF NOT EXISTS idx_reviews_language ON reviews(language);
CREATE INDEX IF NOT EXISTS idx_reviews_quality_status ON reviews(quality_status);
CREATE INDEX IF NOT EXISTS idx_reviews_rating_normalized ON reviews(rating_normalized);

CREATE TABLE IF NOT EXISTS parser_errors (
    id BIGSERIAL PRIMARY KEY,
    parse_run_id BIGINT REFERENCES parse_runs(id) ON DELETE CASCADE,
    stage VARCHAR(100),
    raw_ref TEXT,
    error_code VARCHAR(100),
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS model_runs (
    id BIGSERIAL PRIMARY KEY,
    model_name VARCHAR(150) NOT NULL,
    feature_method VARCHAR(100) NOT NULL,
    train_size INTEGER,
    test_size INTEGER,
    accuracy NUMERIC(6, 4),
    macro_f1 NUMERIC(6, 4),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS review_analysis (
    id BIGSERIAL PRIMARY KEY,
    review_id BIGINT NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
    sentiment_label VARCHAR(20) NOT NULL,
    sentiment_score NUMERIC(8, 6),
    model_name VARCHAR(150),
    feature_method VARCHAR(100),
    predicted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    model_run_id BIGINT REFERENCES model_runs(id) ON DELETE SET NULL,
    CONSTRAINT chk_sentiment_label CHECK (sentiment_label IN ('positive', 'neutral', 'negative', 'unknown')),
    CONSTRAINT uq_review_analysis UNIQUE (review_id, model_name, feature_method)
);

CREATE INDEX IF NOT EXISTS idx_review_analysis_label ON review_analysis(sentiment_label);
