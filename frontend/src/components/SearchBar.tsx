import { useState, FormEvent } from "react";

interface Props {
  onSearch: (phrase: string) => void;
  loading: boolean;
}

export default function SearchBar({ onSearch, loading }: Props) {
  const [value, setValue] = useState("");

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = value.trim();
    if (trimmed) onSearch(trimmed);
  }

  return (
    <form onSubmit={handleSubmit} className="search-form">
      <input
        className="search-input"
        type="text"
        placeholder="Describe a mood, feeling, or phrase..."
        value={value}
        onChange={(e) => setValue(e.target.value)}
        disabled={loading}
        autoFocus
      />
      <button className="search-btn" type="submit" disabled={loading || !value.trim()}>
        {loading ? <span className="spinner" /> : "Find songs"}
      </button>
    </form>
  );
}
