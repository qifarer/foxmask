'use client';

import { useQueryState } from 'nuqs';
import { memo, useEffect } from 'react';

import { FOXMASK_URL_IMPORT_NAME } from '@/const/url';
import { useUserStore } from '@/store/user';

const ImportSettings = memo(() => {
  const [importUrlShareSettings, isUserStateInit] = useUserStore((s) => [
    s.importUrlShareSettings,
    s.isUserStateInit,
  ]);

  // Import settings from the url
  const [searchParam] = useQueryState(FOXMASK_URL_IMPORT_NAME, {
    clearOnDefault: true,
    defaultValue: '',
  });

  useEffect(() => {
    // Why use `usUserStateInit`,
    // see: https://github.com/qifarer/foxmask/pull/4072
    if (searchParam && isUserStateInit) importUrlShareSettings(searchParam);
  }, [searchParam, isUserStateInit]);

  return null;
});

export default ImportSettings;
