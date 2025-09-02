export const MIGRATE_KEY = 'migrated';
export enum UpgradeStatus {
  START,
  UPGRADING,
  UPGRADED,
  UPGRADE_FAILED,
}

export const V1DB_NAME = 'LobeHub';
export const V1DB_TABLE_NAME = 'FOXMASK';

export interface MigrationError {
  message: string;
  stack: string;
}
