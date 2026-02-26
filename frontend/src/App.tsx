import { useState } from "react";
import SearchBar from "./components/SearchBar";
import SongCard from "./components/SongCard";
import { Song, RecommendRequest } from "./types";

export default function App() {
  const [results, setResults] = useState<Song[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastPhrase, setLastPhrase] = useState<string | null>(null);

  async function handleSearch(phrase: string) {
    setLoading(true);
    setError(null);
    setLastPhrase(phrase);

    const body: RecommendRequest = { phrase, n: 5 };

    try {
      const res = await fetch("/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail?.detail ?? `Server error ${res.status}`);
      }

      const data: Song[] = await res.json();
      setResults(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setResults([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1 className="title">Lyric Match</h1>
        <p className="subtitle">
          Enter a phrase or mood — we'll find songs whose lyrics feel the same way.
        </p>
      </header>

      <main className="main">
        <SearchBar onSearch={handleSearch} loading={loading} />

        {error && <div className="error">{error}</div>}

        {!loading && results.length > 0 && (
          <section className="results">
            <h2 className="results-heading">
              Songs matching &ldquo;{lastPhrase}&rdquo;
            </h2>
            <ul className="results-list">
              {results.map((song, i) => (
                <li key={`${song.title}-${song.artist}`}>
                  <SongCard song={song} rank={i + 1} />
                </li>
              ))}
            </ul>
          </section>
        )}

        {!loading && results.length === 0 && lastPhrase && !error && (
          <p className="empty">No results found — try a different phrase.</p>
        )}
      </main>
    </div>
  );
}
