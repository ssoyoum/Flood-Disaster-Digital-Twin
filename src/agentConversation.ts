export type ConversationMessage = { role: "user" | "assistant"; content: string };

// Match AgentConversationTurn's six-message, 1,500-code-point API limits.
export function boundedAgentHistory(history: ConversationMessage[]): ConversationMessage[] {
  return history.filter((turn) => turn.content.trim()).slice(-6).map((turn) => ({
    role: turn.role,
    content: Array.from(turn.content).slice(0, 1500).join(""),
  }));
}
