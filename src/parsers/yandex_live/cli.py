from __future__ import annotations

import argparse

from .pipeline import run_yandex_live_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Yandex Maps live parser pipeline")
    parser.add_argument("--url", required=True, help="Yandex Maps organization reviews URL")
    parser.add_argument("--name", required=True, help="Tourist object name")
    parser.add_argument("--city", required=True, help="City name")
    parser.add_argument("--type", default="cultural_object", help="Object type: museum, hotel, attraction, cultural_object")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--scrolls", type=int, default=25)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--visible", action="store_true")
    parser.add_argument("--debug-html", action="store_true")
    args = parser.parse_args()

    objects, reviews = run_yandex_live_pipeline(
        url=args.url,
        name=args.name,
        city=args.city,
        object_type=args.type,
        limit=args.limit,
        headless=not args.visible if not args.headless else True,
        scrolls=args.scrolls,
        save_debug_html=args.debug_html,
    )
    print(f"objects_processed rows={len(objects)}")
    print(f"reviews_processed rows={len(reviews)}")


if __name__ == "__main__":
    main()
