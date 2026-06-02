# Yandex live parser

Local Selenium ingestion module. It is separated from dashboard by design.

Run:

```powershell
python -m src.main parse-yandex --url "YANDEX_URL" --name "Object name" --city "Өскемен" --type cultural_object --visible --debug-html
```

The parser writes raw files to `data/raw/yandex/`, normalizes them, then updates processed project files.
