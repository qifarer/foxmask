import { supportLocales } from '@/locales/resources';

export const DEFAULT_LANG = 'en-US';
export const FOXMASK_LOCALE_COOKIE = 'FOXMASK_LOCALE';

/**
 * Check if the language is supported
 * @param locale
 */
export const isLocaleNotSupport = (locale: string) => !supportLocales.includes(locale);
