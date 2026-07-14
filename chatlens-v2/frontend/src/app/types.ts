export interface Chat {
  name: string;
  platform: string;
  message_count: number;
}

export interface Message {
  sender: string;
  text: string;
  timestamp: string;
}

export interface ChatStats {
  total_messages: number;
  total_words: number;
  awards?: Record<string, string>;
  top_senders: { name: string; count: number }[];
  activity_by_hour: Record<string, number>;
  activity_by_day: Record<string, number>;
}

export interface GlobalStats {
  total_messages: number;
  total_chats: number;
}

export interface AiCardData {
  label: string;
  body: string;
}

export interface ToastData {
  id: string;
  message: string;
  type: "success" | "error" | "info";
}
