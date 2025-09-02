'use client';

import { useEffect } from 'react';

import { useQueryRoute } from '@/hooks/useQueryRoute';

/**
 * @description: Changelog Modal (intercepting routes fallback when hard refresh)
 * @example: /changelog/modal => /changelog
 * @refs: https://github.com/qifarer/foxmask/discussions/2295#discussioncomment-9290942
 */

const ChangelogModal = () => {
  const router = useQueryRoute();

  useEffect(() => {
    router.replace('/changelog');
  }, []);

  return null;
};

export default ChangelogModal;
