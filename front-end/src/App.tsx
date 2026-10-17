import { FileUpload } from './components/FileUpload';
import { Chat } from './components/Chat';
import { ShieldCheck, Database, Zap } from 'lucide-react';
import { I18nProvider, useI18n } from './i18n/I18nContext';
import { LanguageSwitcher } from './components/LanguageSwitcher';

function Shell() {
  const { t } = useI18n();
  return (
    <div className="min-h-screen bg-ink-950">
      <header className="border-b border-ink-700">
        <div className="max-w-6xl mx-auto px-6 pt-10 pb-14">
          <div className="flex justify-end mb-8">
            <LanguageSwitcher />
          </div>
          <p className="font-mono text-xs text-accent tracking-[0.2em] uppercase mb-5">
            {t('header.eyebrow')}
          </p>
          <h1 className="font-display text-6xl md:text-8xl text-white leading-[0.95]">
            Lore<span className="text-accent">.</span>
          </h1>
          <p className="mt-6 text-lg text-slate-400 max-w-2xl leading-relaxed">
            {t('header.description')}
          </p>

          <div className="mt-12 grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-3xl">
            <div className="border border-ink-700 rounded-lg p-4 bg-ink-900">
              <ShieldCheck className="w-5 h-5 text-accent mb-2" />
              <p className="font-mono text-2xl text-white">{t('stats.tenant.value')}</p>
              <p className="text-xs text-slate-500 mt-1">{t('stats.tenant.label')}</p>
            </div>
            <div className="border border-ink-700 rounded-lg p-4 bg-ink-900">
              <Database className="w-5 h-5 text-accent mb-2" />
              <p className="font-mono text-2xl text-white">{t('stats.embedding.value')}</p>
              <p className="text-xs text-slate-500 mt-1">{t('stats.embedding.label')}</p>
            </div>
            <div className="border border-ink-700 rounded-lg p-4 bg-ink-900">
              <Zap className="w-5 h-5 text-accent mb-2" />
              <p className="font-mono text-2xl text-white">{t('stats.topk.value')}</p>
              <p className="text-xs text-slate-500 mt-1">{t('stats.topk.label')}</p>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-12 grid lg:grid-cols-5 gap-8">
        <div className="lg:col-span-2">
          <FileUpload />
        </div>
        <div className="lg:col-span-3">
          <Chat />
        </div>
      </main>

      <footer className="border-t border-ink-700 mt-8">
        <div className="max-w-6xl mx-auto px-6 py-8 flex flex-col sm:flex-row justify-between gap-3 text-xs text-slate-500 font-mono">
          <span>
            {t('footer.powered')} <span className="text-accent font-semibold">Brenda Tavares</span>
          </span>
          <span>{t('footer.warning')}</span>
        </div>
      </footer>
    </div>
  );
}

function App() {
  return (
    <I18nProvider>
      <Shell />
    </I18nProvider>
  );
}

export default App;