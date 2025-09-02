import { FOXMASK_TRACE_HEADER, FOXMASK_TRACE_ID, TracePayload } from '@/const/trace';

export const getTracePayload = (req: Request): TracePayload | undefined => {
  const header = req.headers.get(FOXMASK_TRACE_HEADER);
  if (!header) return;

  return JSON.parse(Buffer.from(header, 'base64').toString('utf8'));
};

export const getTraceId = (res: Response) => res.headers.get(FOXMASK_TRACE_ID);

const createTracePayload = (data: TracePayload) => {
  const encoder = new TextEncoder();
  const buffer = encoder.encode(JSON.stringify(data));

  return Buffer.from(buffer).toString('base64');
};

export const createTraceHeader = (data: TracePayload) => {
  return { [FOXMASK_TRACE_HEADER]: createTracePayload(data) };
};
