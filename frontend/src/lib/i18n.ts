import i18n from 'i18next'
import LanguageDetector from 'i18next-browser-languagedetector'
import { initReactI18next } from 'react-i18next'

import ar from '@/locales/ar.json'
import en from '@/locales/en.json'

export const RTL_LANGUAGES = ['ar']

/** Base language actually in use ('en' | 'ar'), even when the detector
 * reports a region-qualified locale like ar-SA. */
export function resolvedLanguage(): string {
  return i18n.resolvedLanguage ?? i18n.language.split('-')[0]
}

function applyDocumentDirection() {
  const language = resolvedLanguage()
  document.documentElement.lang = language
  document.documentElement.dir = RTL_LANGUAGES.includes(language) ? 'rtl' : 'ltr'
}

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      ar: { translation: ar },
    },
    fallbackLng: 'en',
    supportedLngs: ['en', 'ar'],
    nonExplicitSupportedLngs: true, // ar-SA browsers resolve to ar
    interpolation: { escapeValue: false },
  })

applyDocumentDirection()
i18n.on('languageChanged', applyDocumentDirection)

export default i18n
