import { TraceNameMap } from '@/types/trace';

export const FOXMASK_TRACE_HEADER = 'X-foxmask-trace';
export const FOXMASK_TRACE_ID = 'X-foxmask-trace-id';
export const FOXMASK_OBSERVATION_ID = 'X-foxmask-observation-id';

export interface TracePayload {
  /**
   * if user allow to trace
   */
  enabled?: boolean;
  observationId?: string;
  /**
   * chat session: agentId or groupId
   */
  sessionId?: string;
  tags?: string[];
  /**
   * chat topicId
   */
  topicId?: string;
  traceId?: string;
  traceName?: TraceNameMap;
  /**
   * user uuid
   */
  userId?: string;
}
