"""Logging filter that adds trace context to log records.

Meant for Scrapy's ``LOG_FORMAT`` (or any stdlib logging setup): it only adds
attributes to records and never configures handlers or formats.
"""


