import { expect, test } from "vitest";
import { boundedAgentHistory, type ConversationMessage } from "./agentConversation";

test("a long previous answer stays within the backend's history contract", () => {
  const history: ConversationMessage[] = [
    ...Array.from({ length: 6 }, (_, index) => ({ role: "user" as const, content: `질문 ${index}` })),
    { role: "assistant", content: "가".repeat(1800) },
    { role: "user", content: "   " },
  ];
  const result = boundedAgentHistory(history);
  expect(result).toHaveLength(6);
  expect(result[0].content).toBe("질문 1");
  expect(result[5].content).toHaveLength(1500);
  expect(history[6].content).toHaveLength(1800);
});

test("Unicode history is truncated by code point without broken surrogate pairs", () => {
  const result = boundedAgentHistory([{ role: "assistant", content: "🌊".repeat(1501) }]);
  expect(Array.from(result[0].content)).toHaveLength(1500);
  expect(result[0].content).toBe("🌊".repeat(1500));
});
