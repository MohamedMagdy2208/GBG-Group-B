export type Language = "en" | "ar";

const STORAGE_KEY = "preferred_language";

const dictionaries: Record<Language, Record<string, string>> = {
  en: {
    "shell.appName": "AI-Powered Lost & Found",
    "shell.tagline": "Airport operations workspace",
    "shell.signIn": "Sign in",
    "shell.signOut": "Log out",
    "shell.sessionExpired": "Your session expired. Please sign in again to continue protected work.",
    "nav.home": "Home",
    "nav.chat": "Chat",
    "nav.report": "Report",
    "nav.status": "Status",
    "nav.dashboard": "Dashboard",
    "nav.addFound": "Add Found",
    "nav.found": "Found",
    "nav.lost": "Lost",
    "nav.matches": "Matches",
    "nav.claims": "Claims",
    "nav.qrScan": "QR Scan",
    "nav.analytics": "Analytics",
    "nav.audit": "Audit",
    "nav.operations": "Operations",
    "nav.demo": "Demo",
    "nav.users": "Users",
    "nav.locations": "Locations",
    "nav.categories": "Categories",
    "nav.settings": "Settings",
    "language.toggle": "AR",
  },
  ar: {
    "shell.appName": "مفقودات المطار بالذكاء الاصطناعي",
    "shell.tagline": "لوحة عمليات المطار",
    "shell.signIn": "تسجيل دخول",
    "shell.signOut": "تسجيل خروج",
    "shell.sessionExpired": "انتهت جلستك، يرجى تسجيل الدخول مرة أخرى.",
    "nav.home": "الرئيسية",
    "nav.chat": "محادثة",
    "nav.report": "بلاغ",
    "nav.status": "حالة البلاغ",
    "nav.dashboard": "اللوحة",
    "nav.addFound": "إضافة مفقود",
    "nav.found": "موجودات",
    "nav.lost": "مفقودات",
    "nav.matches": "تطابقات",
    "nav.claims": "مطالبات",
    "nav.qrScan": "مسح QR",
    "nav.analytics": "تحليلات",
    "nav.audit": "سجل المراجعة",
    "nav.operations": "العمليات",
    "nav.demo": "عرض تجريبي",
    "nav.users": "المستخدمون",
    "nav.locations": "المواقع",
    "nav.categories": "التصنيفات",
    "nav.settings": "الإعدادات",
    "language.toggle": "EN",
  },
};

export function loadLanguage(): Language {
  if (typeof window === "undefined") return "en";
  const stored = window.localStorage.getItem(STORAGE_KEY);
  return stored === "ar" ? "ar" : "en";
}

export function persistLanguage(language: Language): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, language);
  document.documentElement.lang = language;
  document.documentElement.dir = language === "ar" ? "rtl" : "ltr";
}

export function translate(language: Language, key: string): string {
  return dictionaries[language][key] ?? dictionaries.en[key] ?? key;
}
