"use client";

import React, { createContext, useContext, useSyncExternalStore } from "react";
import { translations, type Language } from "./translations";

interface LanguageContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  toggleLanguage: () => void;
  t: (key: string) => string;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

const STORAGE_KEY = "cyverse.lang";

function subscribe(callback: () => void) {
  window.addEventListener("storage", callback);
  window.addEventListener("cyverse-language-change", callback);
  return () => {
    window.removeEventListener("storage", callback);
    window.removeEventListener("cyverse-language-change", callback);
  };
}

function getSnapshot(): Language {
  try {
    const saved = localStorage.getItem(STORAGE_KEY) as Language | null;
    if (saved === "en" || saved === "vi") return saved;
  } catch {
    // Ignore localStorage errors
  }
  return "en";
}

function getServerSnapshot(): Language {
  return "en";
}

function getNestedTranslation(obj: unknown, path: string): string | undefined {
  const parts = path.split(".");
  let current: unknown = obj;
  for (const part of parts) {
    if (current && typeof current === "object" && part in (current as Record<string, unknown>)) {
      current = (current as Record<string, unknown>)[part];
    } else {
      return undefined;
    }
  }
  return typeof current === "string" ? current : undefined;
}

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const language = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  const setLanguage = (lang: Language) => {
    try {
      localStorage.setItem(STORAGE_KEY, lang);
      document.documentElement.lang = lang;
      window.dispatchEvent(new Event("cyverse-language-change"));
    } catch {
      // Ignore localStorage errors
    }
  };

  const toggleLanguage = () => {
    setLanguage(language === "en" ? "vi" : "en");
  };

  const t = (key: string): string => {
    const dict = translations[language];
    const translated = getNestedTranslation(dict, key);
    if (translated) return translated;
    const fallback = getNestedTranslation(translations.en, key);
    return fallback ?? key;
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage, toggleLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    return {
      language: "en" as Language,
      setLanguage: () => {},
      toggleLanguage: () => {},
      t: (key: string) => {
        const fallback = getNestedTranslation(translations.en, key);
        return fallback ?? key;
      },
    };
  }
  return context;
}
