import urllib.parse
from app.db import get_conn, put_conn
from app.embedder import embed


def recommend(phrase: str, n: int = 5) -> list[dict]:
    n = max(3, min(5, n))
    vec = embed(phrase)
    vec_str = "[" + ",".join(str(x) for x in vec) + "]"

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT title, artist,
                       1 - (embedding <=> %s::vector) AS score
                FROM songs
                ORDER BY embedding <=> %s::vector
                LIMIT %s;
                """,
                (vec_str, vec_str, n),
            )
            rows = cur.fetchall()
    finally:
        put_conn(conn)

    results = []
    for title, artist, score in rows:
        query = urllib.parse.quote(f"{title} {artist}")
        results.append(
            {
                "title": title,
                "artist": artist,
                "score": round(float(score), 4),
                "spotify_url": f"https://open.spotify.com/search/{query}",
            }
        )
    return results
