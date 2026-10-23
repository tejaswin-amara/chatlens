export interface Chat {
  name: string;
  platform: string;
  message_count: number;
}

export interface Message {
  id?: number;
  sender: string;
  text: string;
  timestamp: string;
  platform?: string;
  reply_to?: string | null;
  forwarded_from?: string | null;
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

export interface SparkPendingAction {
  id: number;
  ts: number;
  status: string;
  event: string;
}

export interface SparkWriteHistory {
  id: number;
  ts: number;
  kind: string;
  event_id: string;
  undone: boolean;
}

export interface SparkStatus {
  status: string;
  mode: string;
  seen_messages: number;
  message?: string;
  pending: SparkPendingAction[];
  writes: SparkWriteHistory[];
  error?: string;
}

export interface TimetableSlot {
  period: number;
  course: string;
  room: string;
  faculty: string;
  override?: string | null;
  status: "NORMAL" | "OVERRIDE" | "CANCELLED";
}

export interface TodayTimetable {
  date: string;
  day?: string;
  slots: TimetableSlot[];
  message?: string;
}

export interface AcademicMilestone {
  title: string;
  date: string;
  term?: string;
  days_remaining: number;
}

export interface TaskDeadline {
  id: number;
  summary: string;
  status: string;
  created?: number;
}

export interface DeadlinesData {
  today: string;
  milestones: AcademicMilestone[];
  tasks: TaskDeadline[];
}

export interface MonitoringStatus {
  status: string;
  monitored_chat_ids: number[];
  total_monitored_chats: number;
  total_saved_messages: number;
  active_chats: { name: string; message_count: number }[];
  gemini_model: string;
  spark_mode: string;
}

export function cleanSenderName(sender: string): string {
  const cleaned = sender.replace(/^(\+?\d+[\d\s_-]*)/, "").trim();
  if (cleaned.toLowerCase().replace(/\s+/g, " ") === "prudhvi sai kari") {
    return "Prudhvi Sai Kari";
  }
  return cleaned || sender;
}
