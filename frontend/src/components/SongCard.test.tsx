import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import SongCard from "./SongCard";
import { Song } from "../types";

const song: Song = {
  title: "Bohemian Rhapsody",
  artist: "Queen",
  score: 0.87,
  spotify_url: "https://open.spotify.com/track/abc123",
};

describe("SongCard", () => {
  it("renders the song title and artist", () => {
    render(<SongCard song={song} rank={1} />);
    expect(screen.getByText("Bohemian Rhapsody")).toBeInTheDocument();
    expect(screen.getByText("Queen")).toBeInTheDocument();
  });

  it("displays the rank number", () => {
    render(<SongCard song={song} rank={3} />);
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("rounds score to a percentage", () => {
    render(<SongCard song={song} rank={1} />);
    expect(screen.getByText("87% match")).toBeInTheDocument();
  });

  it("rounds a non-whole score correctly", () => {
    const s = { ...song, score: 0.756 };
    render(<SongCard song={s} rank={1} />);
    expect(screen.getByText("76% match")).toBeInTheDocument();
  });

  it("renders the Spotify link with correct href", () => {
    render(<SongCard song={song} rank={1} />);
    const link = screen.getByRole("link", { name: /listen on spotify/i });
    expect(link).toHaveAttribute("href", song.spotify_url);
  });

  it("opens Spotify link in a new tab", () => {
    render(<SongCard song={song} rank={1} />);
    const link = screen.getByRole("link", { name: /listen on spotify/i });
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });
});
