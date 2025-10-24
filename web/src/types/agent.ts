export interface Tool {
  name: string;
  description: string;
}

export interface Suggestion {
  field: string;
  original_value: string;
  suggested_value: string;
  reason: string;
  confidence: string;
  tool_used?: string;
}

export interface AgentResponse {
  status: string;
  suggestions: Suggestion[];
}

export interface ToolsResponse {
  status: string;
  tools: Tool[];
}
