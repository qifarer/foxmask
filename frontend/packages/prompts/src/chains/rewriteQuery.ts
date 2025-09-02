import { DEFAULT_REWRITE_QUERY } from '@foxmask/const';
import { ChatStreamPayload } from '@foxmask/types';

export const chainRewriteQuery = (
  query: string,
  context: string[],
  instruction: string = DEFAULT_REWRITE_QUERY,
): Partial<ChatStreamPayload> => ({
  messages: [
    {
      content: `${instruction}
<chatHistory>
${context.join('\n')}
</chatHistory>
`,
      role: 'system',
    },
    {
      content: `Follow Up Input: ${query}, it's standalone query:`,
      role: 'user',
    },
  ],
});
