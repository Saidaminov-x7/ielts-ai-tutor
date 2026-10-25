export type TabId = 'home' | 'lesson' | 'practice' | 'exam' | 'words' | 'insights' | 'settings' | 'writing'

export interface TaskSummary {
  key: string
  title: string
  minutes: number
  done: boolean
  available: boolean
  new_cards?: number
  due_cards?: number
}

export interface Lesson {
  day: number
  week: number
  week_source_available?: boolean
  daily_focus?: string
  speaking_outcome?: string
  content_granularity?: 'weekly' | 'daily' | 'missing'
  scheduled_vocabulary_count?: number
  due_vocabulary_count?: number
  course_imported: boolean
  topic: string
  grammar: string
  reading: string
  listening: string
  writing: string
  tasks: TaskSummary[]
  remaining: number
}

export interface NotificationSettings {
  reminders_enabled: boolean
  quiet_mode: boolean
  reminder_time: string
  timezone: string
}

export interface CourseResetResult {
  completed_days: 0
  current_day: 1
  streak: 0
}

export interface Bootstrap {
  user: { telegram_id: number }
  gemini_configured: boolean
  dashboard: {
    day: number
    week: number
    topic: string | null
    course_imported: boolean
    completed_days: number
    streak: number
    due_vocabulary: number
  }
  lesson: Lesson
  notifications: NotificationSettings
}

export interface QuizQuestion {
  index: number
  topic: string
  question: string
  options: string[]
}

export interface QuizSession {
  id: number
  questions: QuizQuestion[]
  answers: Record<string, number>
  submitted?: boolean
  result?: QuizResult
}

export interface QuizAnswerResult {
  index: number
  selected: number
  correct_option: string
  correct?: boolean
  explanation: string
  topic?: string
}

export interface QuizResult {
  score: number
  total: number
  percent: number
  results: QuizAnswerResult[]
}

export interface ExamResult extends QuizResult {
  week: number
  note: string
}

export interface ExamSession {
  id: number
  week: number
  deadline: string
  submitted: boolean
  answers: Record<string, number>
  questions: QuizQuestion[]
  result?: ExamResult | null
}

export interface VocabularyWord {
  id: number
  english: string
  translation: string
  transcription: string
  example: string
  topic: string
  mastery: number
  week?: number | null
  pronunciation_hint?: string
  collocation?: string
  collocation_translation?: string
  collocation_transcription?: string
  collocation_pronunciation_hint?: string
}

export interface VocabularyLibrary {
  items: VocabularyWord[]
  count: number
}

export interface VocabularyExample {
  english: string
  translation: string
}

export interface VocabularyExamples {
  items: VocabularyExample[]
  cached: boolean
}

export interface RoadmapWeek {
  week: number
  month: number
  topic: string
  grammar: string
  listening: string
  reading_writing: string
  speaking_outcome: string
  content_granularity: 'weekly'
  current: boolean
}

export interface CourseRoadmap {
  total_weeks: number
  total_days: number
  current_day: number
  current_week: number
  weeks: RoadmapWeek[]
}

export interface DueVocabulary {
  items: VocabularyWord[]
  count: number
}

export interface ActivityItem {
  kind: string
  topic: string
  score: number | null
  completed_at: string
}

export interface Progress {
  day: number
  completed_days: number
  streak: number
  max_streak: number
  activity_count_returned: number
  recent_activity: ActivityItem[]
  recent_writing_bands: number[]
  average_recent_activity_score: number | null
}

export interface LearningError {
  id: number
  topic: string
  exercise: string
  wrong_answer: string
  correct_answer: string
  error_type: string
  explanation: string
  resolved: boolean
  created_at: string
}

export interface ErrorsResponse {
  items: LearningError[]
}

export interface WritingFeedback {
  task_type: string
  estimated_band: number
  criteria: Record<string, number>
  errors: Array<{ wrong: string; correction: string; explanation_ru: string }>
  explanation_ru: string
  recommendations: string[]
  improved_sample: string
  recurring_errors: string[]
  disclaimer: string
}

export interface WritingAttemptSummary {
  id: number
  task_type: string
  estimated_band: number
  created_at: string
  text_available: boolean
}

export interface WritingAttemptDetail extends Omit<WritingAttemptSummary, 'text_available'> {
  submission_text: string | null
  feedback: WritingFeedback
}

export type ApiErrorCode = 'auth' | 'network' | 'server' | 'unknown'

export class ApiError extends Error {
  code: ApiErrorCode
  serverCode?: string

  constructor(message: string, code: ApiErrorCode, serverCode?: string) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.serverCode = serverCode
  }
}
