interface TelegramThemeParams {
  bg_color?: string
  secondary_bg_color?: string
  text_color?: string
  hint_color?: string
  link_color?: string
  button_color?: string
  button_text_color?: string
  accent_text_color?: string
  section_bg_color?: string
  section_header_text_color?: string
  subtitle_text_color?: string
  destructive_text_color?: string
}

interface TelegramWebApp {
  initData: string
  colorScheme: 'light' | 'dark'
  themeParams: TelegramThemeParams
  ready: () => void
  expand: () => void
  onEvent: (eventType: 'themeChanged', callback: () => void) => void
  offEvent: (eventType: 'themeChanged', callback: () => void) => void
  HapticFeedback?: {
    impactOccurred: (style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft') => void
  }
}

interface Window {
  Telegram?: { WebApp?: TelegramWebApp }
}
