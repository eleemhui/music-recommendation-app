import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";
import { Song } from "./types";

const mockSongs: Song[] = [
  { title: "Creep", artist: "Radiohead", score: 0.92, spotify_url: "https://open.spotify.com/track/1" },
  { title: "Mad World", artist: "Tears for Fears", score: 0.85, spotify_url: "https://open.spotify.com/track/2" },
];

function mockFetch(response: object, ok = true, status = 200) {
  return vi.spyOn(global, "fetch").mockResolvedValue({
    ok,
    status,
    json: () => Promise.resolve(response),
  } as Response);
}

beforeEach(() => vi.restoreAllMocks());
afterEach(() => vi.restoreAllMocks());

async function search(phrase: string) {
  await userEvent.type(screen.getByRole("textbox"), phrase);
  await userEvent.click(screen.getByRole("button", { name: /find songs/i }));
}

describe("App", () => {
  it("renders the heading and subtitle", () => {
    render(<App />);
    expect(screen.getByText("Lyric Match")).toBeInTheDocument();
    expect(screen.getByText(/enter a phrase or mood/i)).toBeInTheDocument();
  });

  it("shows song results after a successful search", async () => {
    mockFetch(mockSongs);
    render(<App />);
    await search("feeling lonely");
    await waitFor(() => expect(screen.getByText("Creep")).toBeInTheDocument());
    expect(screen.getByText("Radiohead")).toBeInTheDocument();
    expect(screen.getByText("Mad World")).toBeInTheDocument();
  });

  it("displays the results heading with the searched phrase", async () => {
    mockFetch(mockSongs);
    render(<App />);
    await search("feeling lonely");
    await waitFor(() => expect(screen.getByText(/songs matching/i)).toBeInTheDocument());
    expect(screen.getByText(/feeling lonely/)).toBeInTheDocument();
  });

  it("sends the correct request body to /recommend", async () => {
    const fetchSpy = mockFetch(mockSongs);
    render(<App />);
    await search("upbeat summer");
    await waitFor(() => expect(fetchSpy).toHaveBeenCalled());
    const [url, options] = fetchSpy.mock.calls[0];
    expect(url).toBe("/recommend");
    expect(JSON.parse(options!.body as string)).toEqual({ phrase: "upbeat summer", n: 5 });
  });

  it("shows an error message when the server returns an error", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue({
      ok: false,
      status: 500,
      json: () => Promise.resolve({ detail: "Internal server error" }),
    } as Response);
    render(<App />);
    await search("dark night");
    await waitFor(() => expect(screen.getByText("Internal server error")).toBeInTheDocument());
  });

  it("shows a generic error when response has no detail field", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue({
      ok: false,
      status: 500,
      json: () => Promise.resolve({}),
    } as Response);
    render(<App />);
    await search("dark night");
    await waitFor(() => expect(screen.getByText(/server error 500/i)).toBeInTheDocument());
  });

  it("shows a generic error when fetch itself throws", async () => {
    vi.spyOn(global, "fetch").mockRejectedValue(new Error("Network failure"));
    render(<App />);
    await search("dark night");
    await waitFor(() => expect(screen.getByText("Network failure")).toBeInTheDocument());
  });

  it("shows empty state when search returns no results", async () => {
    mockFetch([]);
    render(<App />);
    await search("obscure phrase xyz");
    await waitFor(() =>
      expect(screen.getByText(/no results found/i)).toBeInTheDocument()
    );
  });

  it("clears results and error on a new search", async () => {
    const fetchSpy = mockFetch(mockSongs);
    render(<App />);
    await search("first query");
    await waitFor(() => expect(screen.getByText("Creep")).toBeInTheDocument());

    fetchSpy.mockResolvedValue({
      ok: false,
      status: 500,
      json: () => Promise.resolve({ detail: "oops" }),
    } as Response);

    await userEvent.clear(screen.getByRole("textbox"));
    await userEvent.type(screen.getByRole("textbox"), "second query");
    await userEvent.click(screen.getByRole("button", { name: /find songs/i }));

    await waitFor(() => expect(screen.getByText("oops")).toBeInTheDocument());
    expect(screen.queryByText("Creep")).not.toBeInTheDocument();
  });
});
