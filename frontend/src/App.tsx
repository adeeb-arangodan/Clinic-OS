import { useTranslation } from 'react-i18next'
import { Route, Routes } from 'react-router-dom'

// Placeholder shell — replaced by login + role-based routing in M0 deliverable 7.
function Home() {
  const { t, i18n } = useTranslation()
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-2">
      <h1 className="text-3xl font-semibold text-primary">{t('app.name')}</h1>
      <p className="text-slate-600">{t('app.tagline')}</p>
      <button
        type="button"
        className="mt-4 rounded border border-slate-300 px-3 py-1 text-sm"
        onClick={() => i18n.changeLanguage(i18n.language === 'ar' ? 'en' : 'ar')}
      >
        {t('common.language')}: {i18n.language === 'ar' ? 'العربية' : 'English'}
      </button>
    </main>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
    </Routes>
  )
}
