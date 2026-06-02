# Example: run Yandex live ingestion locally.
# Do not run Selenium parser from Streamlit Cloud.

python -m src.main parse-yandex `
  --url "https://yandex.kz/maps/org/example/1234567890/reviews/" `
  --name "Нысан атауы" `
  --city "Өскемен" `
  --type "cultural_object" `
  --limit 100 `
  --scrolls 25 `
  --visible `
  --debug-html
