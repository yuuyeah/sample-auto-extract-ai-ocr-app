import React from 'react';
import { Suggestion } from '../types/agent';

interface AgentValidationPanelProps {
  suggestions: Suggestion[];
  onAccept: (suggestion: Suggestion) => void;
  onReject: (suggestion: Suggestion) => void;
}

const AgentValidationPanel: React.FC<AgentValidationPanelProps> = ({
  suggestions,
  onAccept,
  onReject,
}) => {
  if (suggestions.length === 0) {
    return (
      <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded">
        <p className="text-green-800">✓ 問題は検出されませんでした</p>
      </div>
    );
  }

  return (
    <div className="mt-4 space-y-4">
      <h3 className="text-lg font-semibold">エージェント検証結果</h3>
      {suggestions.map((suggestion, index) => (
        <div
          key={index}
          className="p-4 bg-yellow-50 border border-yellow-200 rounded"
        >
          <div className="mb-2">
            <span className="font-semibold">{suggestion.field}</span>
          </div>
          <div className="mb-2 space-y-1">
            <div className="text-sm">
              <span className="text-gray-600">現在: </span>
              <span className="font-mono">{suggestion.original_value}</span>
            </div>
            <div className="text-sm">
              <span className="text-gray-600">提案: </span>
              <span className="font-mono text-blue-600">
                {suggestion.suggested_value}
              </span>
            </div>
          </div>
          <div className="mb-3 text-sm text-gray-700">
            <span className="font-semibold">理由: </span>
            {suggestion.reason}
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => onAccept(suggestion)}
              className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
            >
              採用
            </button>
            <button
              onClick={() => onReject(suggestion)}
              className="px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400"
            >
              却下
            </button>
          </div>
        </div>
      ))}
    </div>
  );
};

export default AgentValidationPanel;
