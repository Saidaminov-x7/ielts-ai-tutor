import { useCallback, useEffect, useRef, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import { api } from './api'
import type {
  ActivityItem,
  Bootstrap,
  DueVocabulary,
  ExamResult,
  ExamSession,
  LearningError,
  Lesson,
  NotificationSettings,
  Progress,
  QuizResult,
  QuizSession,
  TabId,
  VocabularyWord,
  WritingAttemptDetail,
  WritingAttemptSummary,
  WritingFeedback,
} from './types'

const navItems: Array<{ id: TabId; label: string; icon: string }> = [
  { id: 'home', label: 'Today', icon: 'home' },
  { id: 'lesson', label: 'Lesson', icon: 'book' },
  { id: 'practice', label: 'Practice', icon: 'check' },
  { id: 'words', label: 'Words', icon: 'words' },
  { id: 'insights', label: 'Progress', icon: 'chart' },
  { id: 'settings', label: 'Settings', icon: 'settings' },
]

function Icon({ name, size = 20 }: { name: string; size?: number }) {
  const shared = { width: size, height: size, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 1.7, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const, 'aria-hidden': true as const }
  const paths: Record<string, ReactNode> = {
    home: <><path d="m3 10 9-7 9 7" /><path d="M5 9v11h14V9M9 20v-7h6v7" /></>,
    book: <><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v17H6.5A2.5 2.5 0 0 1 4 17.5z" /><path d="M4 17.5A2.5 2.5 0 0 1 6.5 15H20M8 7h8M8 10h6" /></>,
    check: <><path d="M4 12.5 9 17l11-11" /><path d="M20 12v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h10" /></>,
    words: <><path d="M4 5h16M4 10h16M4 15h10M4 20h7" /><path d="m18 16 2 4 2-4" /></>,
    chart: <><path d="M4 19V5M4 19h17" /><path d="m7 15 4-4 3 2 6-7" /><path d="M17 6h3v3" /></>,
    settings: <><circle cx="12" cy="12" r="3" /><path d="m19.4 15 .1.1 1.4 1.1-1.4 2.4-1.7-.6a7.5 7.5 0 0 1-1.7 1l-.3 1.8h-2.8l-.4-1.8a7.5 7.5 0 0 1-1.7-1l-1.7.6-1.4-2.4 1.4-1.1a7 7 0 0 1 0-2l-1.4-1.1 1.4-2.4 1.7.6a7.5 7.5 0 0 1 1.7-1l.4-1.8h2.8l.3 1.8a7.5 7.5 0 0 1 1.7 1l1.7-.6 1.4 2.4-1.4 1.1a7 7 0 0 1 0 2Z" transform="translate(-1 -1) scale(1.08)" /></>,
    arrow: <><path d="M5 12h14M13 6l6 6-6 6" /></>,
    back: <><path d="M19 12H5m6 6-6-6 6-6" /></>,
    clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
    spark: <><path d="m12 3 1.5 6.5L20 12l-6.5 1.5L12 20l-1.5-6.5L4 12l6.5-2.5z" /><path d="m19 3 .6 2.4L22 6l-2.4.6L19 9l-.6-2.4L16 6l2.4-.6z" /></>,
    sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2m0 16v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></>,
    alert: <><path d="M12 3 2.8 19h18.4L12 3Z" /><path d="M12 9v4m0 3h.01" /></>,
    close: <><path d="m6 6 12 12M18 6 6 18" /></>,
  }
  return <svg {...shared}>{paths[name] ?? paths.spark}</svg>
}

function useTelegramTheme() {
  useEffect(() => {
    const webApp = window.Telegram?.WebApp
    const apply = () => {
      if (!webApp) return
      const root = document.documentElement
      const theme = webApp.themeParams
      const vars: Record<string, string | undefined> = {
        '--tg-bg': theme.bg_color,
        '--tg-secondary-bg': theme.secondary_bg_color,
        '--tg-text': theme.text_color,
        '--tg-hint': theme.hint_color,
        '--tg-link': theme.link_color,
        '--tg-button': theme.button_color,
        '--tg-button-text': theme.button_text_color,
        '--tg-accent': theme.accent_text_color,
        '--tg-section': theme.section_bg_color,
        '--tg-section-header': theme.section_header_text_color,
        '--tg-subtitle': theme.subtitle_text_color,
        '--tg-destructive': theme.destructive_text_color,
      }
      Object.entries(vars).forEach(([key, value]) => value && root.style.setProperty(key, value))
      root.dataset.telegramTheme = webApp.colorScheme
      webApp.ready()
      webApp.expand()
    }
    apply()
    webApp?.onEvent('themeChanged', apply)
    return () => webApp?.offEvent('themeChanged', apply)
  }, [])
}

function ErrorNotice({ message, retry }: { message: string; retry?: () => void }) {
  return (
    <div className="notice notice-error" role="alert">
      <Icon name="alert" size={18} />
      <p>{message}</p>
      {retry && <button className="text-button" type="button" onClick={retry}>Try again</button>}
    </div>
  )
}

function LoadingBlock({ label = 'Loading your study space' }: { label?: string }) {
  return <div className="loading-block" role="status" aria-label={label}><span /><span /><span /></div>
}

function EmptyState({ title, children, action }: { title: string; children: ReactNode; action?: ReactNode }) {
  return (
    <div className="empty-state">
      <span className="empty-mark" aria-hidden="true"><Icon name="spark" size={22} /></span>
      <h3>{title}</h3>
      <p>{children}</p>
      {action}
    </div>
  )
}

function Tag({ children, tone = 'quiet' }: { children: ReactNode; tone?: 'quiet' | 'green' | 'amber' }) {
  return <span className={`tag tag-${tone}`}>{children}</span>
}

export default function App() {
  useTelegramTheme()
  const [tab, setTab] = useState<TabId>('home')
  const [visitedTabs, setVisitedTabs] = useState<Set<TabId>>(() => new Set(['home']))
  const [bootstrap, setBootstrap] = useState<Bootstrap | null>(null)
  const [bootstrapError, setBootstrapError] = useState('')
  const [bootstrapLoading, setBootstrapLoading] = useState(true)
  const [activeQuiz, setActiveQuiz] = useState<QuizSession | null>(null)
  const [quizResult, setQuizResult] = useState<QuizResult | null>(null)
  const [activeExam, setActiveExam] = useState<ExamSession | null>(null)
  const [examResult, setExamResult] = useState<ExamResult | null>(null)

  const loadBootstrap = useCallback(async () => {
    setBootstrapLoading(true)
    setBootstrapError('')
    try {
      const value = await api.bootstrap()
      setBootstrap(value)
    } catch (error) {
      setBootstrapError(error instanceof Error ? error.message : 'Could not load your study space.')
    } finally {
      setBootstrapLoading(false)
    }
  }, [])

  useEffect(() => { void loadBootstrap() }, [loadBootstrap])
  useEffect(() => {
    let storedId = ''
    try { storedId = sessionStorage.getItem('ielts-active-quiz-id') ?? '' } catch { return }
    const id = Number(storedId)
    if (!Number.isSafeInteger(id) || id <= 0) return
    void api.getQuiz(id).then((quiz) => {
      setActiveQuiz(quiz)
      if (quiz.result) setQuizResult(quiz.result)
      setVisitedTabs((current) => new Set(current).add('practice'))
    }).catch(() => {
    })
  }, [])
  useEffect(() => {
    let storedId = ''
    try { storedId = sessionStorage.getItem('ielts-active-exam-id') ?? '' } catch { return }
    const id = Number(storedId)
    if (!Number.isSafeInteger(id) || id <= 0) return
    void api.getExam(id).then((exam) => {
      setActiveExam(exam)
      if (exam.result) setExamResult(exam.result)
      setVisitedTabs((current) => new Set(current).add('exam'))
    }).catch(() => {
      try { sessionStorage.removeItem('ielts-active-exam-id') } catch { /* storage may be disabled */ }
    })
  }, [])

  const openTab = (id: TabId) => {
    setTab(id)
    setVisitedTabs((current) => new Set(current).add(id))
  }
  const title = tab === 'writing' ? 'Writing' : tab === 'exam' ? 'Weekly exam' : navItems.find((item) => item.id === tab)?.label ?? 'Today'

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Skip to content</a>
      <aside className="sidebar" aria-label="Main navigation">
        <div className="brand"><span className="brand-mark">i<span>.</span></span><span className="brand-name">IELTS<br /><small>STUDY SPACE</small></span></div>
        <nav className="side-nav">
          <p className="nav-caption">YOUR SPACE</p>
          {navItems.map((item) => <NavButton key={item.id} item={item} active={tab === item.id} onClick={() => openTab(item.id)} />)}
        </nav>
        <div className="sidebar-foot"><div className="focus-seal"><Icon name="spark" size={16} /><span>A little<br />every day.</span></div><span className="sidebar-note">IELTS · Academic</span></div>
      </aside>

      <div className="main-column">
        <header className="topbar">
          <div className="mobile-brand"><span className="brand-mark">i<span>.</span></span><span>STUDY SPACE</span></div>
          <div className="breadcrumbs"><span>My learning</span><span aria-hidden="true">/</span><strong>{title}</strong></div>
          <div className="topbar-right"><span className="today-date">{new Intl.DateTimeFormat('en', { weekday: 'short', month: 'short', day: 'numeric' }).format(new Date())}</span><button className="avatar" type="button" aria-label="Open settings" onClick={() => openTab('settings')}>I</button></div>
        </header>

        <main id="main-content" className="content-wrap" tabIndex={-1}>
          {bootstrapError && <ErrorNotice message={bootstrapError} retry={() => void loadBootstrap()} />}
          {bootstrapLoading && !bootstrap && <LoadingBlock />}
          {visitedTabs.has('home') && <section hidden={tab !== 'home'}><Dashboard bootstrap={bootstrap} loading={bootstrapLoading} onNavigate={openTab} /></section>}
          {visitedTabs.has('lesson') && <section hidden={tab !== 'lesson'}><LessonScreen lesson={bootstrap?.lesson ?? null} loading={bootstrapLoading} error={bootstrapError} retry={() => void loadBootstrap()} refresh={loadBootstrap} onNavigate={openTab} /></section>}
          {visitedTabs.has('practice') && <section hidden={tab !== 'practice'}><PracticeScreen activeQuiz={activeQuiz} setActiveQuiz={setActiveQuiz} result={quizResult} setResult={setQuizResult} onNavigate={openTab} /></section>}
          {visitedTabs.has('exam') && <section hidden={tab !== 'exam'}><ExamScreen activeExam={activeExam} setActiveExam={setActiveExam} result={examResult} setResult={setExamResult} /></section>}
          {visitedTabs.has('words') && <section hidden={tab !== 'words'}><VocabularyScreen /></section>}
          {visitedTabs.has('insights') && <section hidden={tab !== 'insights'}><InsightsScreen /></section>}
          {visitedTabs.has('settings') && <section hidden={tab !== 'settings'}><SettingsScreen settings={bootstrap?.notifications ?? null} onSaved={(settings) => setBootstrap((value) => value ? { ...value, notifications: settings } : value)} /></section>}
          {visitedTabs.has('writing') && <section hidden={tab !== 'writing'}><WritingScreen key={bootstrap?.user.telegram_id ?? 'unauthenticated'} ownerId={bootstrap?.user.telegram_id ?? null} /></section>}
        </main>

        <nav className="mobile-nav" aria-label="Main navigation">
          {navItems.map((item) => <NavButton key={item.id} item={item} active={tab === item.id} onClick={() => openTab(item.id)} compact />)}
        </nav>
      </div>
    </div>
  )
}

function NavButton({ item, active, onClick, compact = false }: { item: { id: TabId; label: string; icon: string }; active: boolean; onClick: () => void; compact?: boolean }) {
  return <button className={`nav-button${active ? ' active' : ''}${compact ? ' compact' : ''}`} type="button" aria-current={active ? 'page' : undefined} onClick={onClick}><Icon name={item.icon} size={19} /><span>{item.label}</span></button>
}

function PageHeading({ eyebrow, title, description, action }: { eyebrow: string; title: string; description?: string; action?: ReactNode }) {
  return <div className="page-heading"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1>{description && <p className="page-description">{description}</p>}</div>{action}</div>
}

function Dashboard({ bootstrap, loading, onNavigate }: { bootstrap: Bootstrap | null; loading: boolean; onNavigate: (id: TabId) => void }) {
  const summary = bootstrap?.dashboard
  const lesson = bootstrap?.lesson
  return (
    <div className="page-stack">
      <section className="welcome-row"><div><p className="eyebrow">YOUR STUDY JOURNAL</p><h1>Make today<br className="mobile-only" /> count<span className="period">.</span></h1><p className="welcome-copy">A focused session is enough to keep your English moving forward.</p></div><div className="today-stamp"><span>DAY</span><strong>{summary?.day ? String(summary.day).padStart(2, '0') : '—'}</strong><small>of your plan</small></div></section>
      {!window.Telegram?.WebApp?.initData && <div className="notice notice-info" role="status"><Icon name="alert" size={18} /><p>Open this study space from your Telegram tutor to load your personal learning data.</p></div>}
      {loading && !bootstrap ? <LoadingBlock /> : null}

      <section className="today-card" aria-labelledby="today-title">
        <div className="today-card-top"><Tag tone={lesson?.course_imported ? 'green' : 'amber'}>{lesson?.course_imported ? 'TODAY’S LESSON' : 'COURSE CONTENT'}</Tag><span className="week-label">{summary?.week ? `WEEK ${String(summary.week).padStart(2, '0')}` : '—'}</span></div>
        <h2 id="today-title">{lesson?.course_imported && lesson.topic ? lesson.topic : 'Your study plan is ready'}</h2>
        <p>{lesson?.course_imported ? 'Pick up where you left off, one clear step at a time.' : 'Lesson material appears here after your course workbook is imported. No sample lesson is shown.'}</p>
        <div className="today-card-bottom"><div className="tiny-meta"><span><Icon name="clock" size={15} /> {lesson?.tasks?.length ? `${lesson.tasks.reduce((sum, task) => sum + task.minutes, 0)} min planned` : 'Ready when you are'}</span>{summary && <span><Icon name="check" size={15} /> {summary.completed_days} days completed</span>}</div><button className="button button-dark" type="button" onClick={() => onNavigate('lesson')}>Open lesson <Icon name="arrow" size={16} /></button></div>
      </section>

      <div className="section-title-row"><div><p className="eyebrow">YOUR ROUTINE</p><h2>Keep the rhythm</h2></div><span className="section-aside">Nothing extra. Just the next step.</span></div>
      <section className="quick-grid" aria-label="Study activities">
        <ActivityCard icon="words" number={summary ? String(summary.due_vocabulary).padStart(2, '0') : '—'} title="Words to review" detail="Spaced practice" onClick={() => onNavigate('words')} />
        <ActivityCard icon="check" number={summary ? `${summary.streak}` : '—'} title="Day streak" detail="A steady habit" onClick={() => onNavigate('insights')} suffix="days" />
        <ActivityCard icon="spark" number="→" title="Quick practice" detail="One question at a time" onClick={() => onNavigate('practice')} />
        <ActivityCard icon="book" number="↗" title="Writing studio" detail="Review a draft with AI" onClick={() => onNavigate('writing')} />
      </section>

      <section className="note-strip"><div className="note-icon"><Icon name="sun" size={18} /></div><p><strong>Small sessions add up.</strong> Your progress reflects saved activity only. No activity yet? Start with a quick practice when it’s available.</p><button className="icon-button" type="button" aria-label="Open progress" onClick={() => onNavigate('insights')}><Icon name="arrow" size={18} /></button></section>
    </div>
  )
}

function ActivityCard({ icon, number, title, detail, onClick, suffix }: { icon: string; number: string; title: string; detail: string; onClick: () => void; suffix?: string }) {
  return <button className="activity-card" type="button" onClick={onClick}><span className="activity-icon"><Icon name={icon} size={18} /></span><span className="activity-number">{number}{suffix && <small> {suffix}</small>}</span><span className="activity-title">{title}</span><span className="activity-detail">{detail}</span><span className="activity-arrow"><Icon name="arrow" size={16} /></span></button>
}

function LessonScreen({ lesson, loading, error, retry, refresh, onNavigate }: { lesson: Lesson | null; loading: boolean; error: string; retry: () => void; refresh: () => Promise<void>; onNavigate: (id: TabId) => void }) {
  const [pendingTask, setPendingTask] = useState<string | null>(null)
  const [failedTask, setFailedTask] = useState<string | null>(null)
  const [taskError, setTaskError] = useState('')
  const [taskNotice, setTaskNotice] = useState('')

  const completeTask = async (taskKey: string) => {
    if (!lesson || pendingTask || !lesson.course_imported) return
    setPendingTask(taskKey)
    setTaskError('')
    setTaskNotice('')
    try {
      const result = await api.completeLessonTask(lesson.day, taskKey)
      setFailedTask(null)
      setTaskNotice(result.day_completed ? 'All available lesson steps are complete. Your next study day is ready.' : 'Step marked complete.')
      await refresh()
    } catch (error) {
      const serverCode = error instanceof Error ? (error as Error & { serverCode?: string }).serverCode : undefined
      if (serverCode === 'course_not_imported') {
        setFailedTask(null)
        setTaskError('Import your course workbook before completing lesson steps.')
      } else if (serverCode === 'task_content_not_imported') {
        setFailedTask(null)
        setTaskError('This step has no imported course material yet. It will become available when the matching lesson content is added.')
      } else if (serverCode === 'stale_day') {
        setFailedTask(null)
        setTaskError('Your study day has changed. The lesson was refreshed.')
        await refresh()
      } else {
        setFailedTask(taskKey)
        setTaskError(error instanceof Error ? error.message : 'Could not save this step. Please try again.')
      }
    } finally {
      setPendingTask(null)
    }
  }
  if (loading && !lesson) return <LoadingBlock label="Loading today's lesson" />
  return (
    <div className="page-stack">
      <PageHeading eyebrow={`DAY ${lesson?.day ?? '—'} · WEEK ${lesson?.week ?? '—'}`} title="Today's lesson" description="Your plan, laid out in one place." />
      {error && !lesson && <ErrorNotice message={error} retry={retry} />}
      {lesson && <>
        <section className="lesson-overview"><div className="lesson-overview-top"><Tag tone={lesson.course_imported ? 'green' : 'amber'}>{lesson.course_imported ? 'COURSE MATERIAL' : 'MATERIAL NOT IMPORTED'}</Tag><span>{lesson.remaining} steps remaining</span></div><h2>{lesson.course_imported && lesson.topic ? lesson.topic : 'The course material will appear here'}</h2><p>{lesson.course_imported ? 'Work through the available material at your own pace.' : 'The source workbook is not available in this study space yet. The outline below reflects the app’s lesson structure only; it does not imply that course content has been loaded.'}</p></section>
        <div className="lesson-layout"><section className="content-panel"><div className="panel-heading"><div><p className="eyebrow">LESSON CONTENT</p><h2>Study material</h2></div><span className="panel-count">{lesson.course_imported ? 'TODAY' : '—'}</span></div>
            <ContentRow label="Grammar" content={lesson.grammar} available={lesson.week_source_available ?? lesson.course_imported} />
            <ContentRow label={lesson.content_granularity === 'weekly' ? 'Reading / Writing' : 'Reading'} content={lesson.reading} available={lesson.week_source_available ?? lesson.course_imported} />
            <ContentRow label="Listening" content={lesson.listening} available={lesson.week_source_available ?? lesson.course_imported} />
            {lesson.speaking_outcome && <ContentRow label="Speaking / result" content={lesson.speaking_outcome} available={lesson.week_source_available ?? false} />}
            {lesson.content_granularity !== 'weekly' && <ContentRow label="Writing prompt" content={lesson.writing} available={lesson.course_imported} />}
            <div className="writing-cta"><div><strong>Have a draft ready?</strong><span>Choose when to request an AI review.</span></div><button className="button button-quiet" type="button" onClick={() => onNavigate('writing')}>Open Writing studio <Icon name="arrow" size={16} /></button></div>
          </section><aside className="tasks-panel"><p className="eyebrow">SESSION OUTLINE</p><h2>{lesson.course_imported ? "Today's steps" : 'Start studying now'}</h2><p className="panel-intro">{lesson.course_imported ? 'Mark a step complete after finishing it. Progress is saved to your study plan.' : 'The course workbook is not loaded, so there are no lesson blocks to complete. These available activities work now.'}</p>
            {taskError && <div className="notice notice-error task-notice" role="alert"><Icon name="alert" size={18} /><p>{taskError}</p>{failedTask && <button className="text-button" type="button" disabled={pendingTask !== null} onClick={() => void completeTask(failedTask)}>Retry</button>}</div>}
            {taskNotice && <div className="notice notice-info task-notice" role="status">{taskNotice}</div>}
            {!lesson.course_imported && <p className="task-import-hint" id="task-import-hint">Your course lessons and vocabulary appear after the source workbook is imported.</p>}
            {lesson.content_granularity === 'weekly' && <p className="task-import-hint">This source is a weekly roadmap; daily prompts are not included in the workbook.</p>}
            {lesson.content_granularity !== 'weekly' && lesson.course_imported && lesson.tasks.some((task) => !task.available) && <p className="task-import-hint" id="task-material-hint">Some steps are unavailable because their matching lesson material has not been imported.</p>}
            {lesson.course_imported ? <ol className="task-list">{lesson.tasks.map((task, index) => {
              const materialUnavailable = lesson.course_imported && !task.available
              const unavailableHintId = `task-unavailable-${task.key}`
              const materialHintId = !lesson.course_imported ? 'task-import-hint' : materialUnavailable ? unavailableHintId : undefined
              const unavailableMessage = 'This step is unavailable until its matching course material is imported.'
              return <li key={task.key} className={task.done ? 'done' : ''}><span className="task-number" aria-hidden="true">{task.done ? '✓' : String(index + 1).padStart(2, '0')}</span><span className="task-name">{task.title}</span><span className="task-time">{task.minutes}m</span>{materialUnavailable && <span className="sr-only" id={unavailableHintId}>{unavailableMessage}</span>}<button className="task-complete-button" type="button" aria-label={task.done ? `${task.title} completed` : `Mark ${task.title} complete`} aria-describedby={materialHintId} title={materialUnavailable ? unavailableMessage : undefined} disabled={task.done || !lesson.course_imported || !task.available || pendingTask !== null} onClick={() => void completeTask(task.key)}>{pendingTask === task.key ? <><span className="button-spinner" aria-hidden="true" /> Saving</> : task.done ? 'Done' : 'Complete'}</button></li>
            })}</ol> : <div className="fallback-activities"><button className="button button-dark button-full" type="button" onClick={() => onNavigate('practice')}>Start the 10-question grammar practice <Icon name="arrow" size={16} /></button><button className="button button-quiet button-full" type="button" onClick={() => onNavigate('words')}>Open your vocabulary <Icon name="arrow" size={16} /></button><button className="button button-quiet button-full" type="button" onClick={() => onNavigate('writing')}>Write an IELTS response <Icon name="arrow" size={16} /></button></div>}</aside></div>
      </>}
    </div>
  )
}

function ContentRow({ label, content, available }: { label: string; content: string; available: boolean }) {
  const body = available ? (content || 'No material is available for this section yet.') : 'Course content will show here when the source material has been imported.'
  return <article className="content-row"><div className="content-row-head"><h3>{label}</h3><Tag tone={available && content ? 'green' : 'quiet'}>{available && content ? 'AVAILABLE' : 'WAITING'}</Tag></div><p className={available && content ? '' : 'muted-copy'}>{body}</p></article>
}

function PracticeScreen({ activeQuiz, setActiveQuiz, result, setResult, onNavigate }: { activeQuiz: QuizSession | null; setActiveQuiz: (quiz: QuizSession | null) => void; result: QuizResult | null; setResult: (result: QuizResult | null) => void; onNavigate: (id: TabId) => void }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [retryAction, setRetryAction] = useState<(() => void) | null>(null)
  const [questionIndex, setQuestionIndex] = useState(0)
  const [saving, setSaving] = useState(false)

  const start = async () => {
    setLoading(true); setError(''); setResult(null)
    try {
      const session = await api.startQuiz()
      setActiveQuiz(session)
      setQuestionIndex(0)
      setRetryAction(null)
      try { sessionStorage.setItem('ielts-active-quiz-id', String(session.id)) } catch { /* the server still retains the session */ }
    }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not start practice.'); setRetryAction(null) }
    finally { setLoading(false) }
  }
  const choose = async (optionIndex: number) => {
    if (!activeQuiz || saving || activeQuiz.submitted) return
    const question = activeQuiz.questions[questionIndex]
    if (!question) return
    setSaving(true); setError('')
    try {
      const updated = await api.answerQuiz(activeQuiz.id, question.index, optionIndex)
      setActiveQuiz(updated)
      setRetryAction(null)
      window.Telegram?.WebApp?.HapticFeedback?.impactOccurred('light')
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Your answer could not be saved.'); setRetryAction(() => () => void choose(optionIndex)) }
    finally { setSaving(false) }
  }
  const submit = async () => {
    if (!activeQuiz || saving) return
    setSaving(true); setError('')
    try {
      const outcome = await api.submitQuiz(activeQuiz.id)
      setResult(outcome)
      setActiveQuiz({ ...activeQuiz, submitted: true, result: outcome })
      setRetryAction(null)
    }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not submit this practice.'); setRetryAction(() => () => void submit()) }
    finally { setSaving(false) }
  }

  const question = activeQuiz?.questions[questionIndex]
  const selected = question && activeQuiz ? activeQuiz.answers[String(question.index)] : undefined
  const done = Boolean(result || activeQuiz?.submitted)
  return (
    <div className="page-stack">
      <PageHeading eyebrow="PRACTICE" title="One question at a time" description="Answer, save your choice, and see your result when you finish." />
      {error && <ErrorNotice message={error} retry={retryAction ?? undefined} />}
      {result ? <QuizOutcome result={result} questions={activeQuiz?.questions ?? []} onAgain={() => { setActiveQuiz(null); setResult(null); try { sessionStorage.removeItem('ielts-active-quiz-id') } catch { /* storage may be disabled */ } void start() }} /> : activeQuiz && question ? <section className="quiz-card" aria-labelledby="quiz-question" aria-busy={saving}>
        <div className="quiz-topline"><Tag>{question.topic || 'PRACTICE'}</Tag><span>QUESTION {String(questionIndex + 1).padStart(2, '0')} <span className="slash">/</span> {String(activeQuiz.questions.length).padStart(2, '0')}</span></div>
        <div className="quiz-progress" aria-label={`Question ${questionIndex + 1} of ${activeQuiz.questions.length}`}><span style={{ width: `${((questionIndex + 1) / activeQuiz.questions.length) * 100}%` }} /></div>
        <h2 id="quiz-question">{question.question}</h2>
        <fieldset className="answer-list"><legend className="sr-only">Choose one answer</legend>{question.options.map((option, index) => <button key={`${index}-${option}`} type="button" className={`answer-option${selected === index ? ' selected' : ''}`} aria-pressed={selected === index} disabled={saving || done} onClick={() => void choose(index)}><span className="option-key">{String.fromCharCode(65 + index)}</span><span>{option}</span>{selected === index && <span className="option-check" aria-hidden="true">✓</span>}</button>)}</fieldset>
        <div className="quiz-footer"><button className="button button-quiet" type="button" disabled={questionIndex === 0 || saving} onClick={() => setQuestionIndex((index) => index - 1)}><Icon name="back" size={16} /> Previous</button><span className="save-status" aria-live="polite">{saving ? 'Saving…' : selected !== undefined ? 'Answer saved' : 'Choose an answer'}</span>{questionIndex < activeQuiz.questions.length - 1 ? <button className="button button-dark" type="button" disabled={saving} onClick={() => setQuestionIndex((index) => index + 1)}>Next <Icon name="arrow" size={16} /></button> : <button className="button button-dark" type="button" disabled={saving} onClick={() => void submit()}>{saving ? 'Submitting…' : 'Finish practice'} <Icon name="check" size={16} /></button>}</div>
      </section> : activeQuiz && activeQuiz.questions.length === 0 ? <EmptyState title="No practice questions yet">There are no questions available for this session. You can check your lesson or return later.</EmptyState> : <section className="practice-intro"><div className="practice-mark"><Icon name="check" size={25} /></div><p className="eyebrow">A SHORT PRACTICE</p><h2>Take a moment to think.</h2><p>Questions come from the tutor’s available learning material. Your result will be saved with your progress.</p>{loading ? <button className="button button-dark" type="button" disabled><span className="button-spinner" /> Preparing…</button> : <button className="button button-dark" type="button" onClick={() => void start()}>Start practice <Icon name="arrow" size={16} /></button>}</section>}
      <section className="exam-entry"><div><p className="eyebrow">A LONGER SESSION</p><h2>Weekly exam</h2><p>Take a timed practice with a 30-minute server deadline. Your answers are saved as you go.</p></div><button className="button button-quiet" type="button" onClick={() => onNavigate('exam')}>Open exam <Icon name="arrow" size={16} /></button></section>
      <div className="related-link"><span>Looking for a focused review?</span><div><button className="text-button" type="button" onClick={() => onNavigate('words')}>Review vocabulary <Icon name="arrow" size={15} /></button><button className="text-button" type="button" onClick={() => onNavigate('writing')}>Open Writing studio <Icon name="arrow" size={15} /></button></div></div>
    </div>
  )
}

function QuizOutcome({ result, questions, onAgain }: { result: QuizResult; questions: QuizSession['questions']; onAgain: () => void }) {
  return <section className="quiz-outcome"><Tag tone="green">PRACTICE SAVED</Tag><div className="outcome-score"><strong>{result.score}<span>/{result.total}</span></strong><span>{result.percent}% correct</span></div><p className="outcome-disclaimer">This is a practice result, not an official IELTS score.</p><div className="result-list">{result.results.map((item, index) => { const question = questions[item.index]; const chosen = item.selected >= 0 ? question?.options[item.selected] : null; return <article className="result-item" key={`${item.topic}-${index}`}><span className={item.correct ? 'result-mark correct' : 'result-mark'}>{item.correct ? '✓' : '!'}</span><div><strong>{item.topic || `Question ${index + 1}`}</strong><p>{chosen ? `Your answer: ${chosen}. ` : 'No answer selected. '}{item.correct ? 'Correct.' : `Correct answer: ${item.correct_option}. `}{item.explanation}</p></div></article> })}</div><button className="button button-dark" type="button" onClick={onAgain}>Try another set <Icon name="arrow" size={16} /></button></section>
}

function ExamScreen({ activeExam, setActiveExam, result, setResult }: { activeExam: ExamSession | null; setActiveExam: (exam: ExamSession | null) => void; result: ExamResult | null; setResult: (result: ExamResult | null) => void }) {
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [retryAction, setRetryAction] = useState<(() => void) | null>(null)
  const [questionIndex, setQuestionIndex] = useState(0)
  const [now, setNow] = useState(() => Date.now())

  const start = async () => {
    setLoading(true); setError(''); setResult(null)
    try {
      const exam = await api.startExam()
      setActiveExam(exam)
      setQuestionIndex(0)
      setRetryAction(null)
      try { sessionStorage.setItem('ielts-active-exam-id', String(exam.id)) } catch { /* the server retains the session */ }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not start the weekly exam.')
      setRetryAction(null)
    } finally { setLoading(false) }
  }

  const choose = async (optionIndex: number) => {
    if (!activeExam || saving || activeExam.submitted || expired) return
    const question = activeExam.questions[questionIndex]
    if (!question) return
    setSaving(true); setError('')
    try {
      const updated = await api.answerExam(activeExam.id, question.index, optionIndex)
      setActiveExam(updated)
      setRetryAction(null)
      window.Telegram?.WebApp?.HapticFeedback?.impactOccurred('light')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Your exam answer could not be saved.')
      if (!Number.isFinite(Date.parse(activeExam.deadline)) || Date.parse(activeExam.deadline) > Date.now()) {
        setRetryAction(() => () => void choose(optionIndex))
      } else {
        setRetryAction(null)
      }
    } finally { setSaving(false) }
  }

  const submit = async () => {
    if (!activeExam || saving) return
    setSaving(true); setError('')
    try {
      const outcome = await api.submitExam(activeExam.id)
      setResult(outcome)
      setActiveExam({ ...activeExam, submitted: true, result: outcome })
      setRetryAction(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not submit the weekly exam.')
      setRetryAction(() => () => void submit())
    } finally { setSaving(false) }
  }

  useEffect(() => {
    if (!activeExam || activeExam.submitted) return
    setNow(Date.now())
    const timer = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(timer)
  }, [activeExam?.deadline, activeExam?.submitted])

  const question = activeExam?.questions[questionIndex]
  const selected = question && activeExam ? activeExam.answers[String(question.index)] : undefined
  const deadlineTime = activeExam ? Date.parse(activeExam.deadline) : NaN
  const secondsLeft = activeExam && Number.isFinite(deadlineTime) ? Math.max(0, Math.ceil((deadlineTime - now) / 1000)) : null
  const expired = secondsLeft === 0
  const formattedTime = secondsLeft === null ? '30:00' : `${String(Math.floor(secondsLeft / 60)).padStart(2, '0')}:${String(secondsLeft % 60).padStart(2, '0')}`
  const done = Boolean(result || activeExam?.submitted)

  return <div className="page-stack">
    <PageHeading eyebrow={`WEEK ${String(activeExam?.week ?? '—').padStart(2, '0')} · TIMED PRACTICE`} title="Weekly exam" description="A separate timed session. Your answers are saved as you go; the server deadline is authoritative." />
    {error && <ErrorNotice message={error} retry={retryAction ?? undefined} />}
    {result ? <ExamOutcome result={result} questions={activeExam?.questions ?? []} onAgain={() => { setActiveExam(null); setResult(null); try { sessionStorage.removeItem('ielts-active-exam-id') } catch { /* storage may be disabled */ } void start() }} /> : activeExam && question ? <section className="quiz-card exam-card" aria-labelledby="exam-question" aria-busy={saving}>
      <div className="exam-status-row"><Tag>{`WEEK ${String(activeExam.week).padStart(2, '0')}`}</Tag><span className={`exam-timer${expired ? ' expired' : ''}`} aria-label={expired ? 'Time is up' : `Time remaining ${Math.floor((secondsLeft ?? 0) / 60)} minutes and ${(secondsLeft ?? 0) % 60} seconds`}><Icon name="clock" size={15} />{formattedTime}</span></div>
      {expired && <div className="notice notice-ai time-expired" role="status"><Icon name="alert" size={17} /><p>Time is up. Your answers have been saved; submit to see the result.</p></div>}
      <div className="exam-progress-copy"><span>QUESTION {String(questionIndex + 1).padStart(2, '0')} / {String(activeExam.questions.length).padStart(2, '0')}</span><span>{Object.keys(activeExam.answers).length} answered</span></div>
      <div className="quiz-progress" aria-label={`Question ${questionIndex + 1} of ${activeExam.questions.length}`}><span style={{ width: `${((questionIndex + 1) / activeExam.questions.length) * 100}%` }} /></div>
      <p className="eyebrow exam-topic">{question.topic || 'WEEKLY EXAM'}</p><h2 id="exam-question">{question.question}</h2>
      <fieldset className="answer-list"><legend className="sr-only">Choose one answer</legend>{question.options.map((option, index) => <button key={`${index}-${option}`} type="button" className={`answer-option${selected === index ? ' selected' : ''}`} aria-pressed={selected === index} disabled={saving || done || expired} onClick={() => void choose(index)}><span className="option-key">{String.fromCharCode(65 + index)}</span><span>{option}</span>{selected === index && <span className="option-check" aria-hidden="true">✓</span>}</button>)}</fieldset>
      <div className="quiz-footer"><button className="button button-quiet" type="button" disabled={questionIndex === 0 || saving} onClick={() => setQuestionIndex((index) => index - 1)}><Icon name="back" size={16} /> Previous</button><span className="save-status" aria-live="polite">{saving ? 'Saving…' : selected !== undefined ? 'Answer saved' : 'Choose an answer'}</span>{!expired && questionIndex < activeExam.questions.length - 1 ? <button className="button button-dark" type="button" disabled={saving} onClick={() => setQuestionIndex((index) => index + 1)}>Next <Icon name="arrow" size={16} /></button> : <button className="button button-dark" type="button" disabled={saving} onClick={() => void submit()}>{saving ? 'Submitting…' : expired ? 'Submit exam' : 'Finish exam'} <Icon name="check" size={16} /></button>}</div>
    </section> : activeExam && activeExam.questions.length === 0 ? <EmptyState title="No exam questions are available">This session has no questions. Return to practice and try again later.</EmptyState> : <section className="practice-intro exam-intro"><div className="practice-mark"><Icon name="clock" size={25} /></div><p className="eyebrow">30-MINUTE SESSION</p><h2>Ready for a longer challenge?</h2><p>The exam is separate from quick practice. Your answers are recorded and graded when you submit.</p>{loading ? <button className="button button-dark" type="button" disabled><span className="button-spinner" /> Preparing…</button> : <button className="button button-dark" type="button" onClick={() => void start()}>Start weekly exam <Icon name="arrow" size={16} /></button>}</section>}
  </div>
}

function ExamOutcome({ result, questions, onAgain }: { result: ExamResult; questions: ExamSession['questions']; onAgain: () => void }) {
  return <section className="quiz-outcome"><Tag tone="green">WEEK {String(result.week).padStart(2, '0')} · SAVED</Tag><div className="outcome-score"><strong>{result.score}<span>/{result.total}</span></strong><span>{result.percent}% correct</span></div><p className="outcome-disclaimer">{result.note || 'This is a practice result, not an official IELTS score.'}</p><div className="result-list">{result.results.map((item, index) => { const question = questions[item.index]; const chosen = item.selected >= 0 ? question?.options[item.selected] : null; return <article className="result-item" key={`${item.topic}-${index}`}><span className={item.correct ? 'result-mark correct' : 'result-mark'}>{item.correct ? '✓' : '!'}</span><div><strong>{item.topic || `Question ${index + 1}`}</strong><p>{chosen ? `Your answer: ${chosen}. ` : 'No answer selected. '}{item.correct ? 'Correct.' : `Correct answer: ${item.correct_option}. `}{item.explanation}</p></div></article> })}</div><button className="button button-dark" type="button" onClick={onAgain}>Start another exam <Icon name="arrow" size={16} /></button></section>
}

function VocabularyScreen() {
  const [data, setData] = useState<DueVocabulary | null>(null)
  const [library, setLibrary] = useState<VocabularyWord[]>([])
  const [search, setSearch] = useState('')
  const [libraryOpen, setLibraryOpen] = useState(true)
  const [question, setQuestion] = useState('')
  const [tutorAnswer, setTutorAnswer] = useState('')
  const [tutorBusy, setTutorBusy] = useState(false)
  const [tutorError, setTutorError] = useState('')
  const [libraryLoading, setLibraryLoading] = useState(true)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [retryAction, setRetryAction] = useState<(() => void) | null>(null)
  const [index, setIndex] = useState(0)
  const [revealed, setRevealed] = useState(false)
  const [saving, setSaving] = useState(false)
  const [reviewed, setReviewed] = useState(0)
  const load = useCallback(async () => {
    setLoading(true); setError('')
    try { setData(await api.dueVocabulary()); setIndex(0); setRevealed(false); setRetryAction(null) }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not load vocabulary.'); setRetryAction(() => () => void load()) }
    finally { setLoading(false) }
  }, [])
  useEffect(() => { void load() }, [load])
  useEffect(() => {
    let cancelled = false
    setLibraryLoading(true)
    void api.vocabularyLibrary(search).then((result) => { if (!cancelled) setLibrary(result.items) })
      .catch(() => { if (!cancelled) setLibrary([]) })
      .finally(() => { if (!cancelled) setLibraryLoading(false) })
    return () => { cancelled = true }
  }, [search])
  const askTutor = async (event: FormEvent) => {
    event.preventDefault()
    if (!question.trim() || tutorBusy) return
    setTutorBusy(true); setTutorError(''); setTutorAnswer('')
    try { setTutorAnswer((await api.askTutor(question.trim())).answer) }
    catch (reason) { setTutorError(reason instanceof Error ? reason.message : 'Tutor is unavailable.') }
    finally { setTutorBusy(false) }
  }
  const words = data?.items ?? []
  const word: VocabularyWord | undefined = words[index]
  const review = async (correct: boolean) => {
    if (!word || saving) return
    setSaving(true); setError('')
    try {
      await api.reviewVocabulary(word.id, correct)
      setRetryAction(null)
      setReviewed((value) => value + 1)
      setIndex((value) => value + 1)
      setRevealed(false)
      window.Telegram?.WebApp?.HapticFeedback?.impactOccurred(correct ? 'light' : 'soft')
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Your review could not be saved.'); setRetryAction(() => () => void load()) }
    finally { setSaving(false) }
  }
  return <div className="page-stack"><PageHeading eyebrow="VOCABULARY" title="Words worth keeping" description="Recall first, reveal after. Your review is saved to the tutor." action={<button className="button button-quiet" type="button" onClick={() => void load()} disabled={loading}><Icon name="spark" size={16} /> Refresh</button>} />
    <section className="content-panel"><div className="panel-heading"><div><p className="eyebrow">YOUR COURSE LIBRARY</p><h2>Search 900 source words</h2></div><button className="text-button" type="button" onClick={() => setLibraryOpen((value) => !value)}>{libraryOpen ? 'Hide' : 'Show'}</button></div>{libraryOpen && <><label className="field-label" htmlFor="vocabulary-search">Search English, Russian or collocations</label><input id="vocabulary-search" className="text-input" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="e.g. environment" />{libraryLoading ? <LoadingBlock label="Searching course words" /> : library.length ? <div className="activity-list">{library.slice(0, 20).map((item) => <article className="activity-row" key={item.id}><div className="activity-row-main"><strong lang="en">{item.english}</strong><span>{item.transcription && `/${item.transcription}/`} · {item.translation}</span>{item.collocation && <span lang="en">{item.collocation} — {item.collocation_translation} {item.collocation_transcription && `/${item.collocation_transcription}/`}</span>}</div><Tag tone="quiet">W{item.week ?? '–'}</Tag></article>)}</div> : <EmptyState title={search ? 'No matching words' : 'Course words are not loaded'}>{search ? 'Try another spelling or search a collocation.' : 'The source vocabulary will appear after course import.'}</EmptyState>}</>}</section>
    <section className="content-panel"><p className="eyebrow">COURSE QUESTION</p><h2>Ask about this week</h2><form className="settings-form" onSubmit={(event) => void askTutor(event)}><label className="field-label" htmlFor="course-question">Question for your tutor</label><textarea id="course-question" className="text-area" rows={3} maxLength={1000} value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask about this week's topic or words" /><button className="button button-dark" type="submit" disabled={tutorBusy || !question.trim()}>{tutorBusy ? 'Thinking…' : 'Ask Gemini'}</button></form>{tutorError && <ErrorNotice message={tutorError} />}{tutorAnswer && <p className="muted-copy" role="status">{tutorAnswer}</p>}</section>
    {error && <ErrorNotice message={error} retry={retryAction ?? undefined} />}{loading ? <LoadingBlock label="Loading words to review" /> : !word ? <EmptyState title={reviewed ? 'Review complete' : 'Nothing due right now'}>{reviewed ? `${reviewed} ${reviewed === 1 ? 'word' : 'words'} reviewed in this session. Your next set appears when it is due.` : 'Your due vocabulary list is empty. New words will appear here when the tutor has material for you.'}</EmptyState> : <section className="word-review" aria-live="polite"><div className="word-review-top"><Tag>{word.topic || 'VOCABULARY'}</Tag><span>{index + 1} of {data?.count ?? words.length}</span></div><div className="word-card"><p className="eyebrow">WORD {String(index + 1).padStart(2, '0')}</p><h2 lang="en">{word.english}</h2>{word.transcription && <span className="transcription">/{word.transcription}/</span>}{revealed ? <div className="word-answer"><p className="translation">{word.translation}</p>{word.example && <p className="example" lang="en">“{word.example}”</p>}</div> : <p className="recall-prompt">Take a moment to remember what it means.</p>}</div>{!revealed ? <button className="button button-dark button-full" type="button" onClick={() => setRevealed(true)}>Reveal meaning <Icon name="spark" size={16} /></button> : <div className="review-actions"><button className="button button-quiet" type="button" disabled={saving} onClick={() => void review(false)}>Need practice</button><button className="button button-dark" type="button" disabled={saving} onClick={() => void review(true)}>{saving ? 'Saving…' : 'I remembered'} <Icon name="check" size={16} /></button></div>}{saving && <span className="sr-only" role="status">Saving vocabulary review</span>}</section>}
    <p className="support-note">Your answers help schedule the next review. They are not displayed as a language proficiency score.</p></div>
}

function InsightsScreen() {
  const [progress, setProgress] = useState<Progress | null>(null)
  const [errors, setErrors] = useState<LearningError[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const [summary, errorList] = await Promise.all([api.progress(), api.errors()])
      setProgress(summary); setErrors(errorList.items)
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not load progress.') }
    finally { setLoading(false) }
  }, [])
  useEffect(() => { void load() }, [load])
  return <div className="page-stack"><PageHeading eyebrow="YOUR RECORD" title="Progress, kept honest" description="A record of saved learning activity. No activity means no numbers to show." action={<button className="button button-quiet" type="button" onClick={() => void load()} disabled={loading}><Icon name="spark" size={16} /> Refresh</button>} />
    {error && <ErrorNotice message={error} retry={() => void load()} />}{loading ? <LoadingBlock label="Loading progress and review notes" /> : progress && <>
      <section className="metrics-row" aria-label="Saved learning totals"><Metric label="Days completed" value={String(progress.completed_days)} /><Metric label="Current streak" value={String(progress.streak)} suffix="days" /><Metric label="Best streak" value={String(progress.max_streak)} suffix="days" /><Metric label="Activities returned" value={String(progress.activity_count_returned)} /></section>
      <div className="insights-layout"><section className="content-panel"><div className="panel-heading"><div><p className="eyebrow">RECENT ACTIVITY</p><h2>Your latest work</h2></div><span className="panel-count">{progress.recent_activity.length} ITEMS</span></div>{progress.recent_activity.length ? <div className="activity-list">{progress.recent_activity.map((item: ActivityItem, index) => <ActivityRow key={`${item.completed_at}-${index}`} activity={item} />)}</div> : <EmptyState title="No saved activity yet">Finish a supported practice to start building your personal record.</EmptyState>}</section>
        <aside className="content-panel errors-panel"><div className="panel-heading"><div><p className="eyebrow">REVIEW NOTES</p><h2>Patterns to revisit</h2></div><span className="panel-count">{errors.length} ITEMS</span></div>{errors.length ? <div className="error-list">{errors.map((item) => <article className="error-item" key={item.id}><div className="error-item-head"><Tag tone="amber">{item.error_type}</Tag><time>{formatDate(item.created_at)}</time></div><h3>{item.topic}</h3>{item.exercise && <p className="error-exercise">{item.exercise}</p>}<p><span className="wrong-answer">Recorded selection: {item.wrong_answer}</span><span className="correct-answer">Correct answer: {item.correct_answer}</span></p>{item.explanation && <p className="muted-copy">{item.explanation}</p>}</article>)}</div> : <EmptyState title="No review notes">Mistakes saved during objective practice will appear here for another look.</EmptyState>}</aside></div>
      {progress.recent_writing_bands.length > 0 && <div className="notice notice-info"><Icon name="alert" size={18} /><p>Recent AI writing estimates: {progress.recent_writing_bands.join(' · ')}. These are learning estimates, not official IELTS band scores.</p></div>}
      {progress.average_recent_activity_score !== null && <p className="support-note">Average of returned recent activities: {progress.average_recent_activity_score}%. This reflects saved practice, not an IELTS result.</p>}
    </>}</div>
}

function Metric({ label, value, suffix }: { label: string; value: string; suffix?: string }) {
  return <div className="metric-card"><span>{label}</span><strong>{value}{suffix && <small> {suffix}</small>}</strong></div>
}

function ActivityRow({ activity }: { activity: ActivityItem }) {
  return <article className="activity-row"><span className="activity-row-mark"><Icon name={activity.kind === 'writing' ? 'spark' : activity.kind === 'quiz' ? 'check' : 'book'} size={17} /></span><div className="activity-row-main"><strong>{activity.topic || activity.kind}</strong><span>{activity.kind} · {formatDate(activity.completed_at)}</span></div><span className="activity-row-score">{activity.score === null ? '—' : `${activity.score}%`}</span></article>
}

function formatDate(value: string) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric' }).format(date)
}

function SettingsScreen({ settings, onSaved }: { settings: NotificationSettings | null; onSaved: (settings: NotificationSettings) => void }) {
  const [draft, setDraft] = useState<NotificationSettings | null>(settings)
  const [loading, setLoading] = useState(!settings)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [retryAction, setRetryAction] = useState<(() => void) | null>(null)
  const [saved, setSaved] = useState(false)
  useEffect(() => { if (settings) { setDraft(settings); setLoading(false) } }, [settings])
  const load = useCallback(async () => {
    setLoading(true); setError('')
    try { const value = await api.settings(); setDraft(value); onSaved(value); setRetryAction(null) }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not load settings.'); setRetryAction(() => () => void load()) }
    finally { setLoading(false) }
  }, [onSaved])
  useEffect(() => { if (!settings) void load() }, [load, settings])
  const save = async () => {
    if (!draft) return
    setSaving(true); setSaved(false); setError('')
    try { const value = await api.saveSettings({ reminders_enabled: draft.reminders_enabled, quiet_mode: draft.quiet_mode, reminder_time: draft.reminder_time }); setDraft(value); onSaved(value); setSaved(true); setRetryAction(null) }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Your settings could not be saved.'); setRetryAction(() => () => void save()) }
    finally { setSaving(false) }
  }
  return <div className="page-stack"><PageHeading eyebrow="PREFERENCES" title="Make it yours" description="Set how the tutor fits into your day." />
    {error && <ErrorNotice message={error} retry={retryAction ?? undefined} />}{loading ? <LoadingBlock label="Loading notification settings" /> : draft && <><section className="settings-panel"><div className="panel-heading"><div><p className="eyebrow">TELEGRAM REMINDERS</p><h2>A nudge at the right time</h2></div><Tag tone="green">SAVED SETTINGS</Tag></div><p className="panel-intro">Reminder messages are sent by your Telegram tutor. Your device notification permissions are controlled in Telegram.</p>
      <SwitchRow id="reminders" label="Daily study reminder" description="Receive a reminder at your selected time." checked={draft.reminders_enabled} onChange={(checked) => { setDraft({ ...draft, reminders_enabled: checked }); setSaved(false) }} />
      <SwitchRow id="quiet" label="Quiet mode" description="Pause non-essential tutor messages." checked={draft.quiet_mode} onChange={(checked) => { setDraft({ ...draft, quiet_mode: checked }); setSaved(false) }} />
      <div className="setting-time"><div><label htmlFor="reminder-time">Reminder time</label><p>Local time · {draft.timezone}</p></div><input id="reminder-time" type="time" value={draft.reminder_time} disabled={!draft.reminders_enabled} onChange={(event) => { setDraft({ ...draft, reminder_time: event.target.value }); setSaved(false) }} /></div>
      <div className="setting-save"><span className="save-status" role="status" aria-live="polite">{saved ? 'Changes saved' : 'Changes are not saved yet'}</span><button className="button button-dark" type="button" disabled={saving || saved} onClick={() => void save()}>{saving ? 'Saving…' : 'Save settings'} <Icon name="check" size={16} /></button></div>
    </section><p className="support-note">Settings apply to this tutor account. This page does not request browser or device notification permissions.</p></>}</div>
}

function SwitchRow({ id, label, description, checked, onChange }: { id: string; label: string; description: string; checked: boolean; onChange: (checked: boolean) => void }) {
  return <div className="switch-row"><div><label htmlFor={id}>{label}</label><p>{description}</p></div><input id={id} className="switch-input" type="checkbox" role="switch" checked={checked} onChange={(event) => onChange(event.target.checked)} /></div>
}

function WritingScreen({ ownerId }: { ownerId: number | null }) {
  const [text, setText] = useState('')
  const [taskType, setTaskType] = useState('task_2')
  const [draftOwner, setDraftOwner] = useState<number | null>(null)
  const [draftStatus, setDraftStatus] = useState('Draft storage is unavailable until your Telegram account is loaded.')
  const [consented, setConsented] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [feedback, setFeedback] = useState<WritingFeedback | null>(null)
  const [attempts, setAttempts] = useState<WritingAttemptSummary[]>([])
  const [historyLoading, setHistoryLoading] = useState(true)
  const [historyError, setHistoryError] = useState('')
  const [selectedAttempts, setSelectedAttempts] = useState<number[]>([])
  const [attemptDetails, setAttemptDetails] = useState<Record<number, WritingAttemptDetail>>({})
  const [detailLoading, setDetailLoading] = useState<number[]>([])
  const [detailErrors, setDetailErrors] = useState<Record<number, string>>({})
  const evaluationRequest = useRef(0)
  const loadHistory = useCallback(async () => {
    setHistoryLoading(true)
    setHistoryError('')
    try {
      const result = await api.writingAttempts(50)
      setAttempts(result.items)
      setSelectedAttempts((selected) => selected.filter((id) => result.items.some((attempt) => attempt.id === id && attempt.text_available)))
    } catch (reason) {
      setHistoryError(reason instanceof Error ? reason.message : 'Could not load your writing history.')
    } finally {
      setHistoryLoading(false)
    }
  }, [])
  useEffect(() => { void loadHistory() }, [loadHistory])
  useEffect(() => {
    evaluationRequest.current += 1
    setText('')
    setTaskType('task_2')
    setLoading(false)
    setFeedback(null)
    setConsented(false)
    setDraftOwner(null)
    if (ownerId === null) {
      setDraftStatus('Draft storage is unavailable until your Telegram account is loaded.')
      return
    }

    try {
      const saved = window.localStorage.getItem(`ielts-writing-draft:${ownerId}`)
      if (saved) {
        const draft: unknown = JSON.parse(saved)
        if (typeof draft === 'object' && draft !== null && 'text' in draft && typeof draft.text === 'string' && 'taskType' in draft && typeof draft.taskType === 'string' && ['task_1', 'task_2', 'auto'].includes(draft.taskType)) {
          setText(draft.text)
          setTaskType(draft.taskType)
          setDraftStatus('Draft restored from this browser.')
        } else {
          setDraftStatus('Saved draft could not be read. A new draft can be saved in this browser.')
        }
      } else {
        setDraftStatus('Draft will be saved in this browser as you write.')
      }
    } catch {
      setDraftStatus('Browser storage failed. Recent edits may not be saved, and an older draft may remain in this browser profile.')
      return
    }
    setDraftOwner(ownerId)
  }, [ownerId])

  useEffect(() => {
    if (ownerId === null || draftOwner !== ownerId) return
    setDraftStatus('Saving draft…')
    const timeout = window.setTimeout(() => {
      try {
        const key = `ielts-writing-draft:${ownerId}`
        if (text.length === 0) {
          window.localStorage.removeItem(key)
          setDraftStatus('Draft cleared from this browser.')
        } else {
          window.localStorage.setItem(key, JSON.stringify({ text, taskType }))
          setDraftStatus('Draft saved in this browser.')
        }
      } catch {
        setDraftStatus('Browser storage failed. Recent edits may not be saved, and an older draft may remain in this browser profile.')
      }
    }, 500)
    return () => window.clearTimeout(timeout)
  }, [draftOwner, ownerId, taskType, text])
  const clearDraft = () => {
    setText('')
    setFeedback(null)
    setConsented(false)
    if (ownerId !== null) {
      try {
        window.localStorage.removeItem(`ielts-writing-draft:${ownerId}`)
        setDraftStatus('Draft cleared from this browser.')
      } catch {
        setDraftStatus('Could not clear the saved draft from browser storage.')
      }
    }
  }
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (text.trim().length < 50 || !consented) return
    const requestId = evaluationRequest.current + 1
    evaluationRequest.current = requestId
    setLoading(true); setError(''); setFeedback(null)
    try {
      const result = await api.evaluateWriting(text.trim(), taskType)
      if (evaluationRequest.current === requestId) {
        setFeedback(result)
        void loadHistory()
      }
    } catch (reason) {
      if (evaluationRequest.current === requestId) {
        setError(reason instanceof Error ? reason.message : 'The writing review could not be completed.')
      }
    } finally {
      if (evaluationRequest.current === requestId) setLoading(false)
    }
  }
  const toggleComparison = async (attempt: WritingAttemptSummary) => {
    if (!attempt.text_available) return
    if (selectedAttempts.includes(attempt.id)) {
      setSelectedAttempts((current) => current.filter((id) => id !== attempt.id))
      return
    }
    if (selectedAttempts.length >= 2) return
    setSelectedAttempts((current) => [...current, attempt.id])
    if (attemptDetails[attempt.id]) return
    setDetailLoading((current) => [...current, attempt.id])
    setDetailErrors((current) => { const next = { ...current }; delete next[attempt.id]; return next })
    try {
      const detail = await api.writingAttempt(attempt.id)
      if (detail.submission_text === null) {
        setDetailErrors((current) => ({ ...current, [attempt.id]: 'This saved attempt does not contain essay text and cannot be compared.' }))
      }
      setAttemptDetails((current) => ({ ...current, [attempt.id]: detail }))
    } catch (reason) {
      setDetailErrors((current) => ({ ...current, [attempt.id]: reason instanceof Error ? reason.message : 'Could not load this saved essay.' }))
    } finally {
      setDetailLoading((current) => current.filter((id) => id !== attempt.id))
    }
  }
  const retryDetail = (attempt: WritingAttemptSummary) => {
    setDetailErrors((current) => { const next = { ...current }; delete next[attempt.id]; return next })
    setDetailLoading((current) => [...current, attempt.id])
    void api.writingAttempt(attempt.id).then((detail) => {
      setAttemptDetails((current) => ({ ...current, [attempt.id]: detail }))
    }).catch((reason: unknown) => {
      setDetailErrors((current) => ({ ...current, [attempt.id]: reason instanceof Error ? reason.message : 'Could not load this saved essay.' }))
    }).finally(() => setDetailLoading((current) => current.filter((id) => id !== attempt.id)))
  }
  const comparisonReady = selectedAttempts.length === 2 && selectedAttempts.every((id) => attemptDetails[id]?.submission_text !== null && attemptDetails[id] !== undefined)
  return <div className="page-stack"><PageHeading eyebrow="WRITING STUDIO" title="Work through your draft" description="Bring a response you have written. Ask for AI feedback only when you are ready." />
    <div className="notice notice-ai"><Icon name="alert" size={18} /><p><strong>Before you request feedback:</strong> your writing will be sent to the configured AI provider. The review uses the tutor’s limited AI budget. It is an estimate for learning and is not an official IELTS score.</p></div>
    <p className="support-note">When you request a review, your essay and feedback are saved to your tutor account so you can view writing history. The browser copy remains in this profile until you clear or overwrite it.</p>
    {error && <ErrorNotice message={error} />}
    <form className="writing-form" onSubmit={(event) => void submit(event)}>
      <div className="writing-controls"><div className="field"><label htmlFor="writing-task">Task type</label><select id="writing-task" value={taskType} disabled={loading} onChange={(event) => setTaskType(event.target.value)}><option value="task_1">Academic Task 1</option><option value="task_2">Academic Task 2</option><option value="auto">Help me identify the task</option></select></div><span className="field-note"><Icon name="clock" size={15} /> Take your time</span></div>
      <div className="field"><label htmlFor="writing-text">Your response</label><textarea id="writing-text" value={text} disabled={loading} onChange={(event) => { setText(event.target.value); setFeedback(null) }} rows={12} placeholder="Write or paste your response here…" aria-describedby="writing-length writing-help writing-draft-status" aria-invalid={text.length > 0 && text.trim().length < 50} /><div className="writing-meta"><span id="writing-length" className={text.length > 0 && text.trim().length < 50 ? 'field-error' : ''} aria-live="polite">{text.length} characters · at least 50 to request feedback</span><span id="writing-help">Your draft is saved in this browser profile in local browser storage. Anyone with profile access can read it. It is not sent to AI until requested.</span></div><p id="writing-draft-status" className="save-status" role="status" aria-live="polite">{draftStatus}</p></div>
      <label className="consent-row"><input type="checkbox" checked={consented} onChange={(event) => setConsented(event.target.checked)} /><span>I understand this sends my writing to AI and uses the tutor’s limited AI budget.</span></label>
      <div className="writing-submit"><p>Nothing is sent until you press the button.</p><button className="button button-dark" type="submit" disabled={loading || text.trim().length < 50 || !consented}>{loading ? <><span className="button-spinner" /> Reviewing…</> : <>Request AI feedback <Icon name="spark" size={16} /></>}</button></div>
    {text && <button className="text-button" type="button" disabled={loading} onClick={clearDraft}>Clear saved draft</button>}
    </form>
    {feedback && <WritingResult feedback={feedback} />}
    <section className="content-panel" aria-labelledby="writing-history-title">
      <div className="panel-heading"><div><p className="eyebrow">YOUR WORK</p><h2 id="writing-history-title">Writing history</h2></div><button className="text-button" type="button" onClick={() => void loadHistory()} disabled={historyLoading}>{historyLoading ? 'Refreshing…' : 'Refresh history'}</button></div>
      <p className="panel-intro">Saved essays are private to your tutor account. Choose up to two saved essay versions to compare their text side by side.</p>
      {historyLoading && <LoadingBlock label="Loading writing history" />}
      {historyError && <ErrorNotice message={historyError} retry={() => void loadHistory()} />}
      {!historyLoading && !historyError && attempts.length === 0 && <EmptyState title="No reviewed essays yet">Your writing attempts will appear here after you request AI feedback.</EmptyState>}
      {!historyLoading && !historyError && attempts.length > 0 && <div className="history-list" aria-label="Saved writing attempts">
        {attempts.map((attempt) => {
          const selected = selectedAttempts.includes(attempt.id)
          const label = `${attempt.task_type.replaceAll('_', ' ')} · band ${attempt.estimated_band.toFixed(1)} · ${new Date(attempt.created_at).toLocaleString()}`
          return <article className="content-row" key={attempt.id}>
            <div className="content-row-main"><strong>{label}</strong>{!attempt.text_available && <p>This older attempt has feedback only; its essay text was not saved, so it cannot be compared.</p>}
              {detailLoading.includes(attempt.id) && <p role="status">Loading saved attempt…</p>}
              {detailErrors[attempt.id] && <ErrorNotice message={detailErrors[attempt.id]} retry={() => retryDetail(attempt)} />}
              {!attemptDetails[attempt.id] && !detailErrors[attempt.id] && !detailLoading.includes(attempt.id) && <button className="text-button" type="button" onClick={() => retryDetail(attempt)}>View saved feedback</button>}
              {attemptDetails[attempt.id]?.feedback && <details className="sample-details"><summary>View saved feedback</summary><WritingResult feedback={attemptDetails[attempt.id].feedback} /></details>}
            </div>
            {attempt.text_available && <button className="button button-quiet" type="button" aria-pressed={selected} disabled={!selected && selectedAttempts.length >= 2} onClick={() => void toggleComparison(attempt)}>{selected ? 'Remove from comparison' : 'Select to compare'}</button>}
          </article>
        })}
      </div>}
      {comparisonReady && <div className="feedback-section" aria-labelledby="writing-compare-title"><h3 id="writing-compare-title">Essay version comparison</h3><div className="lesson-layout">{selectedAttempts.map((id) => {
        const attempt = attemptDetails[id]
        if (!attempt?.submission_text) return null
        return <section className="content-panel" key={id}><p className="eyebrow">{attempt.task_type.replaceAll('_', ' ')} · {new Date(attempt.created_at).toLocaleString()}</p><h4>Estimated band {attempt.estimated_band.toFixed(1)}</h4><p style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{attempt.submission_text}</p></section>
      })}</div><button className="text-button" type="button" onClick={() => setSelectedAttempts([])}>Clear comparison</button></div>}
    </section>
  </div>
}

function WritingResult({ feedback }: { feedback: WritingFeedback }) {
  const criterionNames: Record<string, string> = { task_achievement_response: 'Task response', coherence_cohesion: 'Coherence & cohesion', lexical_resource: 'Lexical resource', grammatical_range_accuracy: 'Grammar range & accuracy' }
  return <section className="writing-result" aria-labelledby="writing-result-title"><div className="result-heading"><div><p className="eyebrow">AI WRITING REVIEW</p><h2 id="writing-result-title">Feedback for your draft</h2></div><div className="band-estimate"><strong>{feedback.estimated_band.toFixed(1)}</strong><span>estimated / 9</span></div></div><p className="notice notice-ai"><Icon name="alert" size={18} />{feedback.disclaimer}</p><p>{feedback.explanation_ru}</p><div className="criteria-grid">{Object.entries(feedback.criteria).map(([key, value]) => <div className="criterion" key={key}><span>{criterionNames[key] ?? key.replaceAll('_', ' ')}</span><strong>{value}</strong></div>)}</div>{feedback.errors.length > 0 && <div className="feedback-section"><h3>Specific corrections</h3>{feedback.errors.map((item, index) => <article className="feedback-error" key={`${item.wrong}-${index}`}><p><span className="wrong-answer">{item.wrong}</span><span aria-hidden="true"> → </span><span className="correct-answer">{item.correction}</span></p><p>{item.explanation_ru}</p></article>)}</div>}{feedback.recommendations.length > 0 && <div className="feedback-section"><h3>Next steps</h3><ul>{feedback.recommendations.map((item) => <li key={item}>{item}</li>)}</ul></div>}{feedback.improved_sample && <details className="sample-details"><summary>Read an improved sample</summary><p>{feedback.improved_sample}</p></details>}</section>
}

export { WritingScreen }

