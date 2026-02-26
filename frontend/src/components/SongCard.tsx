import { Song } from "../types";

interface Props {
  song: Song;
  rank: number;
}

export default function SongCard({ song, rank }: Props) {
  const pct = Math.round(song.score * 100);

  return (
    <div className="song-card">
      <div className="song-rank">{rank}</div>
      <div className="song-info">
        <div className="song-title">{song.title}</div>
        <div className="song-artist">{song.artist}</div>
      </div>
      <div className="song-right">
        <div className="song-score" title="Lyric similarity">
          {pct}% match
        </div>
        <a
          className="spotify-btn"
          href={song.spotify_url}
          target="_blank"
          rel="noopener noreferrer"
        >
          Listen on Spotify
        </a>
      </div>
    </div>
  );
}
