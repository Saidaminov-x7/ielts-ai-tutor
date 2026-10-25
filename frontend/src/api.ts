import {
  ApiError,
  type Bootstrap,
  type DueVocabulary,
  type ExamResult,
  type ExamSession,
  type ErrorsResponse,
  type Lesson,
  type NotificationSettings,
  type Progress,
  type QuizResult,
  type QuizSession,
  type WritingFeedback,
  type WritingAttemptDetail,
  type WritingAttemptSummary,
  type VocabularyLibrary,
  type VocabularyExamples,
  type CourseRoadmap,
  type CourseResetResult,
} from './types'

const API_ROOT = '/api/v1'
let authFailure: ApiError | null = null

function initData(): string {
  return window.Telegram?.WebApp?.initData ?? ''
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  if (authFailure) throw authFailure
  const data = initData()
  if (!data) {
    throw new ApiError(
      'Telegram did not provide signed launch data. Close this window, then reopen the app from the tutor’s private chat using /start and “Open app”.',
      'auth',
    )
  }

  let response: Response
  try {
    response = await fetch(`${API_ROOT}${path}`, {
      ...init,
      headers: {
        Accept: 'application/json',
        Authorization: `tma ${data}`,
        ...(init.body ? { 'Content-Type': 'application/json' } : {}),
        ...init.headers,
      },
    })
  } catch {
    throw new ApiError('Could not reach the study service. Check your connection and retry.', 'network')
  }

  if (response.status === 401 || response.status === 403) {
    authFailure = new ApiError('Telegram could not verify this session. Close and reopen the Mini App from your tutor.', 'auth')
    window.dispatchEvent(new CustomEvent('ielts-auth-error', { detail: authFailure.message }))
    throw authFailure
  }

  const payload: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    const body = payload as { message?: unknown; error?: unknown; code?: unknown } | null
    const nestedError = typeof body?.error === 'object' && body.error !== null
      ? body.error as { code?: unknown; message?: unknown }
      : null
    const detail = nestedError?.message ?? body?.message
    const message = typeof detail === 'string' ? detail : 'The study service is unavailable right now.'
    const serverCode = typeof nestedError?.code === 'string'
      ? nestedError.code
      : typeof body?.code === 'string' ? body.code : typeof body?.error === 'string' ? body.error : undefined
    throw new ApiError(message, response.status >= 500 ? 'server' : 'unknown', serverCode)
  }
  return payload as T
}

const json = (method: 'POST' | 'PUT' | 'PATCH', body?: unknown): RequestInit => ({
  method,
  ...(body === undefined ? {} : { body: JSON.stringify(body) }),
})

export const api = {
  bootstrap: () => request<Bootstrap>('/bootstrap'),
  lesson: () => request<Lesson>('/lesson/current'),
  roadmap: () => request<CourseRoadmap>('/course/roadmap'),
  completeLessonTask: (dayNumber: number, taskKey: string) => request<{ lesson: Lesson; day_completed: boolean }>(
    `/lesson/${dayNumber}/tasks/${encodeURIComponent(taskKey)}/complete`, json('POST'),
  ),
  startQuiz: () => request<QuizSession>('/quiz/sessions', json('POST')),
  getQuiz: (id: number) => request<QuizSession>(`/quiz/sessions/${id}`),
  answerQuiz: (id: number, questionIndex: number, optionIndex: number) =>
    request<QuizSession>(`/quiz/sessions/${id}/answers`, json('PUT', {
      question_index: questionIndex,
      option_index: optionIndex,
    })),
  submitQuiz: (id: number) => request<QuizResult>(`/quiz/sessions/${id}/submit`, json('POST')),
  dueVocabulary: () => request<DueVocabulary>('/vocabulary/due'),
  vocabularyLibrary: (query = '', week?: number) => request<VocabularyLibrary>(
    `/vocabulary/library?q=${encodeURIComponent(query)}${week ? `&week=${week}` : ''}`,
  ),
  askTutor: (question: string) => request<{ answer: string; week: number }>(
    '/learning/tutor', json('POST', { question }),
  ),
  reviewVocabulary: (id: number, correct: boolean) =>
    request<DueVocabulary['items'][number]>(`/vocabulary/${id}/review`, json('POST', { correct })),
  vocabularyExamples: async (id: number): Promise<VocabularyExamples> => {
    const result = await request<VocabularyExamples>(`/vocabulary/${id}/examples`, json('POST'))
    if (!result || !Array.isArray(result.items) || result.items.length !== 10 || typeof result.cached !== 'boolean'
      || result.items.some((item) => !item || typeof item.english !== 'string' || !item.english.trim()
        || typeof item.translation !== 'string' || !item.translation.trim())) {
      throw new ApiError('The tutor returned an incomplete example set. Please retry.', 'unknown', 'invalid_examples_response')
    }
    return result
  },
  startExam: () => request<ExamSession>('/exam/sessions', json('POST')),
  getExam: (id: number) => request<ExamSession>(`/exam/sessions/${id}`),
  answerExam: (id: number, questionIndex: number, answerIndex: number) =>
    request<ExamSession>(`/exam/sessions/${id}/answers`, json('PUT', {
      question_index: questionIndex,
      answer_index: answerIndex,
    })),
  submitExam: (id: number) => request<ExamResult>(`/exam/sessions/${id}/submit`, json('POST')),
  progress: () => request<Progress>('/progress'),
  errors: () => request<ErrorsResponse>('/errors'),
  settings: () => request<NotificationSettings>('/settings/notifications'),
  saveSettings: (settings: Partial<NotificationSettings>) =>
    request<NotificationSettings>('/settings/notifications', json('PATCH', settings)),
  resetCourse: (requestId: string) => request<CourseResetResult>(
    '/learning/reset', json('POST', { confirm: true, request_id: requestId }),
  ),
  evaluateWriting: (text: string, taskType: string) => request<WritingFeedback>(
    '/writing/evaluate', json('POST', { text, task_type: taskType }),
  ),
  writingAttempts: (limit = 50) => request<{ items: WritingAttemptSummary[] }>(`/writing/attempts?limit=${limit}`),
  writingAttempt: (id: number) => request<WritingAttemptDetail>(`/writing/attempts/${id}`),
}
