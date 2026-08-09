FROM python:3.12-slim

WORKDIR /app

# No extra pip deps — scraper uses stdlib only.
COPY .cursor/skills/shopify_scrape/scripts/scrape_shopify_catalog.py /app/scrape_shopify_catalog.py
COPY shopify/shopify_product_import_example.csv /app/shopify_product_import_example.csv

RUN mkdir -p /data/out /data/sitemaps

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python3", "/app/scrape_shopify_catalog.py"]
CMD ["--help"]
