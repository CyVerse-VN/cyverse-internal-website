import os

# Set before application imports so tests never use the configured cloud database.
os.environ["DATABASE_URL"] = (
    "postgresql+psycopg://test:test@127.0.0.1:5432/cyverse_internal_test"
)
os.environ["THREADS_ENABLED"] = "false"
os.environ["THREADS_EMBEDDED_WORKER"] = "true"
os.environ["THREADS_ACCOUNTS"] = "[]"
