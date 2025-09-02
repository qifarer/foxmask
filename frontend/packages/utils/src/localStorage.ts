const PREV_KEY = 'FOXMASK_GLOBAL';

// FOXMASK_PREFERENCE for userStore
// FOXMASK_GLOBAL_PREFERENCE for globalStore
type StorageKey = 'FOXMASK_PREFERENCE' | 'FOXMASK_SYSTEM_STATUS';

export class AsyncLocalStorage<State> {
  private storageKey: StorageKey;

  constructor(storageKey: StorageKey) {
    this.storageKey = storageKey;

    // skip server side rendering
    if (typeof window === 'undefined') return;

    // migrate old data
    if (localStorage.getItem(PREV_KEY)) {
      const data = JSON.parse(localStorage.getItem(PREV_KEY) || '{}');

      const preference = data.state.preference;

      if (data.state?.preference) {
        localStorage.setItem('FOXMASK_PREFERENCE', JSON.stringify(preference));
      }
      localStorage.removeItem(PREV_KEY);
    }
  }

  async saveToLocalStorage(state: object) {
    const data = await this.getFromLocalStorage();

    localStorage.setItem(this.storageKey, JSON.stringify({ ...data, ...state }));
  }

  async getFromLocalStorage(key: StorageKey = this.storageKey): Promise<State> {
    return JSON.parse(localStorage.getItem(key) || '{}');
  }
}
