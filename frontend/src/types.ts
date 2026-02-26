export interface Song {
  title: string;
  artist: string;
  score: number;
  spotify_url: string;
}

export interface RecommendRequest {
  phrase: string;
  n: number;
}
