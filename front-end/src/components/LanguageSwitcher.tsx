import { Languages } from 'lucide-react';
import { useI18n } from '../i18n/I18nContext';
import type { Locale } from '../i18n/I18nContext';

const options: { value: Locale; label: string }[] = [
  { value: 'pt-BR', label: 'PT' },
  { value: 'en', label: 'EN' },
  { value: 'zh-CN', label: '中文' },
];

export function LanguageSwitcher() {
  const { locale, setLocale } = useI18n();
  return (
    <div className="flex items-center gap-1 border border-ink-700 rounded-lg p-1 bg-ink-900">
      <Languages className="w-4 h-4 text-slate-500 mx-1" />
      {options.map(opt => (
        <button
          key={opt.value}
          onClick={() => setLocale(opt.value)}
          className={`px-2.5 py-1 rounded text-xs font-mono transition-colors ${
            locale === opt.value
              ? 'bg-accent text-ink-950 font-semibold'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}