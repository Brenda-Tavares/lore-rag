import { createContext, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { ptBR } from './locales/pt-BR';
import { en } from './locales/en';
import { zhCN } from './locales/zh-CN';

export type Locale = 'pt-BR' | 'en' | 'zh-CN';

const dictionaries: Record<Locale, Record<string, string>> = {
  'pt-BR': ptBR,
  en,
  'zh-CN': zhCN,
};

interface I18nContextValue {
  locale: Locale;
  setLocale: (l: Locale) => void;
  t: (key: string, vars?: Record<string, string>) => string;
}

const I18nContext = createContext<I18nContextValue | undefined>(undefined);

const STORAGE_KEY = 'lore.locale';

function detectLocale(): Locale {
  const stored = localStorage.getItem(STORAGE_KEY) as Locale | null;
  if (stored && stored in dictionaries) return stored;
  const nav = navigator.language;
  if (nav.startsWith('zh')) return 'zh-CN';
  if (nav.startsWith('pt')) return 'pt-BR';
  return 'en';
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocale] = useState<Locale>(detectLocale);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, locale);
    document.documentElement.lang = locale;
  }, [locale]);

  const t = (key: string, vars?: Record<string, string>) => {
    let str = dictionaries[locale][key] ?? dictionaries['en'][key] ?? key;
    if (vars) {
      for (const [k, v] of Object.entries(vars)) {
        str = str.replace(`{${k}}`, v);
      }
    }
    return str;
  };

  return (
    <I18nContext.Provider value={{ locale, setLocale, t }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n() {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error('useI18n must be used within I18nProvider');
  return ctx;
}