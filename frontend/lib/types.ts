export interface Message {
  role: "user" | "assistant";
  content: string;
}

export interface Metrics {
  turnNum: number;
  avgProductScore: number;
  totalTokens: number;
  episodicChunks: number;
  preferenceChunks: number;
  factsExtracted: number;
  summaryCreated: boolean;
  scores: number[];
}
