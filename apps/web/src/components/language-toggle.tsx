"use client";

import * as React from "react";
import { Languages } from "lucide-react";
import { useLanguage } from "@/lib/i18n/context";
import { Button } from "@/components/ui/button";

export function LanguageToggle({ className }: { className?: string }) {
  const { language, toggleLanguage } = useLanguage();

  return (
    <Button
      variant="ghost"
      size="sm"
      className={`h-9 px-2.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors font-semibold text-xs flex items-center gap-1.5 ${className ?? ""}`}
      onClick={toggleLanguage}
      aria-label={language === "en" ? "Switch to Vietnamese" : "Chuyển sang Tiếng Anh"}
      title={language === "en" ? "Chuyển sang Tiếng Việt" : "Switch to English"}
    >
      <Languages className="h-4 w-4 text-slate-600 dark:text-slate-300" />
      <span className="uppercase text-slate-700 dark:text-slate-200 tracking-wider font-bold">
        {language === "en" ? "EN" : "VI"}
      </span>
    </Button>
  );
}
