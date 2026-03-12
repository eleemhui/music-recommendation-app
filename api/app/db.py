import os
from psycopg2.pool import SimpleConnectionPool

_pool: SimpleConnectionPool | None = None


def get_pool() -> SimpleConnectionPool:
    global _pool
    if _pool is None:
        _pool = SimpleConnectionPool(1, 10, dsn=os.environ["DATABASE_URL"])
    return _pool


def get_conn():
    return get_pool().getconn()


def put_conn(conn) -> None:
    get_pool().putconn(conn)


def init_db() -> None:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS songs (
                    id        SERIAL PRIMARY KEY,
                    title     TEXT NOT NULL,
                    artist    TEXT NOT NULL,
                    embedding vector(384) NOT NULL
                );
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS songs_embedding_hnsw
                    ON songs USING hnsw (embedding vector_cosine_ops);
            """)
        conn.commit()
    finally:
        put_conn(conn)


def songs_empty() -> bool:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM songs;")
            return cur.fetchone()[0] == 0  # type: ignore[index]
    finally:
        put_conn(conn)
