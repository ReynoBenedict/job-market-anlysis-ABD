"""Common Crawl as a source of archived job pages (schema.org JobPosting markup).

Discovery uses the columnar URL index (Parquet, queried remotely with DuckDB, as Common
Crawl recommends for bulk work). Only matching records are then downloaded, one HTTP
range request per archived page; whole WARC files are never downloaded.
"""

ARCHIVE_ROOT = "https://data.commoncrawl.org"
INDEX_SERVER = "https://index.commoncrawl.org"
