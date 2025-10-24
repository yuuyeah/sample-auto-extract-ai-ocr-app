import React, { useState, useEffect } from 'react';
import { Field } from '../types/app-schema';
import { Suggestion, Tool } from '../types/agent';

interface ExtractedInfoDisplayProps {
  extractedInfo: Record<string, any>;
  fields: Field[];
  appDisplayName: string;
  onSave: () => void;
  onHighlightField: (field: string, stayOnExtractionView?: boolean) => void;
  onHighlightCell: (fieldName: string, rowIndex: number, columnName: string) => void;
  onUpdateExtractedInfo: (info: Record<string, any>) => void;
  onRunAgent?: () => Promise<Suggestion[]>;
  agentStatus?: 'idle' | 'running' | 'completed';
  onGetTools?: () => Promise<Tool[]>;
}

const ExtractedInfoDisplay: React.FC<ExtractedInfoDisplayProps> = ({
  extractedInfo,
  fields,
  appDisplayName,
  onSave,
  onHighlightField,
  onHighlightCell,
  onUpdateExtractedInfo,
  onRunAgent,
  agentStatus = 'idle',
  onGetTools,
}) => {
  const [editMode, setEditMode] = useState(false);
  const [editedInfo, setEditedInfo] = useState<Record<string, any>>(extractedInfo);
  const [originalInfo, setOriginalInfo] = useState<Record<string, any>>(extractedInfo);
  const [agentSuggestions, setAgentSuggestions] = useState<Suggestion[]>([]);
  const [showToolsModal, setShowToolsModal] = useState(false);
  const [tools, setTools] = useState<Tool[]>([]);

  // 外部からのextractedInfoの変更を監視して、編集中でなければ更新
  useEffect(() => {
    if (!editMode) {
      setEditedInfo({...extractedInfo});
      setOriginalInfo({...extractedInfo});
    }
  }, [extractedInfo, editMode]);

  // ページ読み込み時にツール一覧を取得
  useEffect(() => {
    if (onGetTools) {
      handleShowToolsLoad();
    }
  }, [onGetTools]);

  const handleShowToolsLoad = async () => {
    if (!onGetTools) return;
    
    try {
      const toolsList = await onGetTools();
      setTools(toolsList);
    } catch (error) {
      console.error('ツール取得エラー:', error);
    }
  };

  // 編集モードの切り替え
  const toggleEditMode = () => {
    if (editMode) {
      // 編集モードを終了して変更を保存
      // 親コンポーネントに編集後のデータを渡す
      console.log("編集後のデータ:", editedInfo);
      onUpdateExtractedInfo(editedInfo);
      
      // 少し遅延させてから保存処理を実行（状態更新が反映されるのを待つ）
      setTimeout(() => {
        onSave();
      }, 100);
    }
    setEditMode(!editMode);
  };

  // エージェント実行
  const handleRunAgent = async () => {
    if (!onRunAgent) return;
    
    try {
      const suggestions = await onRunAgent();
      setAgentSuggestions(suggestions);
    } catch (error) {
      console.error('エージェント実行エラー:', error);
    }
  };

  // ツール一覧を表示
  const handleShowTools = () => {
    setShowToolsModal(true);
  };

  // 提案を採用
  const handleAcceptSuggestion = (suggestion: Suggestion) => {
    // 編集モードでない場合は確認ダイアログを表示
    if (!editMode) {
      const confirmed = window.confirm('編集画面に移動して修正を適用しますか？');
      if (!confirmed) return;
      setEditMode(true);
    }
    
    let newInfo = { ...editedInfo };
    
    // フィールドパスを解析（例: "client_info.address" -> ["client_info", "address"]）
    const fieldPath = suggestion.field.split('.');
    
    if (fieldPath.length === 1) {
      // トップレベルフィールド
      newInfo[fieldPath[0]] = suggestion.suggested_value;
    } else if (fieldPath.length === 2) {
      // ネストされたフィールド（例: client_info.address）
      const [parentField, childField] = fieldPath;
      newInfo[parentField] = {
        ...(newInfo[parentField] || {}),
        [childField]: suggestion.suggested_value
      };
    }
    
    setEditedInfo(newInfo);
    onUpdateExtractedInfo(newInfo);
    
    // 採用した提案を削除
    setAgentSuggestions(prev => 
      prev.filter(s => s.field !== suggestion.field)
    );
  };

  // 提案を却下
  const handleRejectSuggestion = (suggestion: Suggestion) => {
    setAgentSuggestions(prev => 
      prev.filter(s => s.field !== suggestion.field)
    );
  };

  // 編集をキャンセルして元に戻す
  const cancelEdit = () => {
    setEditedInfo({...originalInfo});
    setEditMode(false);
  };

  // フィールド値の更新
  const updateFieldValue = (fieldName: string, value: any) => {
    const newEditedInfo = {
      ...editedInfo,
      [fieldName]: value
    };
    setEditedInfo(newEditedInfo);
    
    // 即時に親コンポーネントにも通知
    // これにより、編集中のデータがリアルタイムで親コンポーネントに反映される
    onUpdateExtractedInfo(newEditedInfo);
  };

  // マップフィールドの値を更新
  const updateMapFieldValue = (fieldName: string, subFieldName: string, value: any) => {
    const currentMap = editedInfo[fieldName] || {};
    const updatedMap = {
      ...currentMap,
      [subFieldName]: value
    };
    
    setEditedInfo(prev => ({
      ...prev,
      [fieldName]: updatedMap
    }));
  };

  // リストフィールドのアイテムを更新
  const updateListItem = (fieldName: string, itemIndex: number, itemValue: any) => {
    const currentList = [...(editedInfo[fieldName] || [])];
    currentList[itemIndex] = itemValue;
    
    setEditedInfo(prev => ({
      ...prev,
      [fieldName]: currentList
    }));
  };

  // リストフィールドのアイテムのプロパティを更新
  const updateListItemProperty = (fieldName: string, itemIndex: number, propertyName: string, value: any) => {
    const currentList = [...(editedInfo[fieldName] || [])];
    if (!currentList[itemIndex]) {
      currentList[itemIndex] = {};
    }
    
    currentList[itemIndex] = {
      ...currentList[itemIndex],
      [propertyName]: value
    };
    
    setEditedInfo(prev => ({
      ...prev,
      [fieldName]: currentList
    }));
  };

  // フィールドの表示
  const renderField = (field: Field) => {
    if (field.type === 'string') {
      return renderStringField(field);
    }
    else if (field.type === 'map' && field.fields) {
      return renderMapField(field);
    }
    else if (field.type === 'list' && field.items) {
      return renderListField(field);
    }
    // デフォルトはシンプルなテキストフィールドとして表示
    else {
      return renderStringField(field);
    }
  };

  // フィールドに対応する修正提案を取得
  const getSuggestionForField = (fieldName: string) => {
    return agentSuggestions.find(s => s.field === fieldName);
  };

  // 修正提案の表示
  const renderSuggestion = (suggestion: Suggestion) => {
    return (
      <div className="mt-2 p-3 bg-yellow-50 border border-yellow-300 rounded">
        <div className="text-sm mb-2">
          <div className="font-semibold text-yellow-800 mb-1">
            {suggestion.tool_used && `${suggestion.tool_used}経由で確認済み`}
          </div>
          <div className="mb-1">
            「{suggestion.original_value}」→「{suggestion.suggested_value}」の表記ゆれを検出
          </div>
          <div className="text-gray-700">
            提案値: {suggestion.suggested_value}
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => handleAcceptSuggestion(suggestion)}
            className="px-3 py-1 bg-blue-500 text-white text-sm rounded hover:bg-blue-600"
          >
            採用する
          </button>
          <button
            onClick={() => handleRejectSuggestion(suggestion)}
            className="px-3 py-1 bg-gray-300 text-gray-700 text-sm rounded hover:bg-gray-400"
          >
            却下
          </button>
        </div>
      </div>
    );
  };

  // 文字列フィールドの表示
  const renderStringField = (field: Field) => {
    const value = editMode ? editedInfo[field.name] : extractedInfo[field.name];
    const suggestion = getSuggestionForField(field.name);
    
    return (
      <div key={field.name} className="mb-4">
        <div className="flex justify-between items-center mb-1">
          <label className="block text-sm font-medium text-gray-700">
            {field.display_name} {suggestion && <span className="text-yellow-600">⚠</span>}
          </label>
        </div>
        
        {editMode ? (
          <div className="relative">
            <input
              type="text"
              value={value || ''}
              onChange={(e) => updateFieldValue(field.name, e.target.value)}
              className="w-full p-2 border border-gray-300 rounded"
              onFocus={() => onHighlightField(field.name, true)}
            />
            <button
              type="button"
              onClick={() => onHighlightField(field.name, true)}
              className="absolute right-2 top-2 text-blue-500 hover:text-blue-700"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
            </button>
          </div>
        ) : (
          <div 
            className="p-2 bg-gray-50 border border-gray-200 rounded cursor-pointer hover:bg-gray-100"
            onClick={() => onHighlightField(field.name, true)}
          >
            {value || '(抽出されませんでした)'}
          </div>
        )}
        {suggestion && renderSuggestion(suggestion)}
      </div>
    );
  };

  // マップフィールドの表示
  const renderMapField = (field: Field) => {
    if (!field.fields) return null;
    
    const mapValue = editMode ? editedInfo[field.name] || {} : extractedInfo[field.name] || {};
    
    return (
      <div key={field.name} className="mb-6">
        <h3 className="text-lg font-medium mb-2">{field.display_name}</h3>
        <div className="pl-4 border-l-2 border-gray-200 space-y-3">
          {field.fields.map(subField => {
            const fieldPath = `${field.name}.${subField.name}`;
            const suggestion = getSuggestionForField(fieldPath);
            
            return (
              <div key={subField.name} className="mb-3">
                <div className="flex justify-between items-center mb-1">
                  <label className="block text-sm font-medium text-gray-700">
                    {subField.display_name} {suggestion && <span className="text-yellow-600">⚠</span>}
                  </label>
                </div>
                
                {editMode ? (
                  <div className="relative">
                    <input
                      type="text"
                      value={mapValue[subField.name] || ''}
                      onChange={(e) => updateMapFieldValue(field.name, subField.name, e.target.value)}
                      className="w-full p-2 border border-gray-300 rounded"
                      onFocus={() => onHighlightField(fieldPath, true)}
                    />
                    <button
                      type="button"
                      onClick={() => onHighlightField(fieldPath, true)}
                      className="absolute right-2 top-2 text-blue-500 hover:text-blue-700"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                    </button>
                  </div>
                ) : (
                  <div 
                    className="p-2 bg-gray-50 border border-gray-200 rounded cursor-pointer hover:bg-gray-100"
                    onClick={() => onHighlightField(fieldPath, true)}
                  >
                    {mapValue[subField.name] || '(抽出されませんでした)'}
                  </div>
                )}
                {suggestion && renderSuggestion(suggestion)}
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  // リストフィールドの表示
  const renderListField = (field: Field) => {
    if (!field.items) return null;
    
    const listData = editMode ? editedInfo[field.name] || [] : extractedInfo[field.name] || [];
    
    // マップ型のリストの場合
    if (field.items.type === 'map' && field.items.fields) {
      return (
        <div key={field.name} className="mb-6">
          <h3 className="text-lg font-medium mb-2">{field.display_name}</h3>
          
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  {field.items.fields.map((itemField) => (
                    <th 
                      key={itemField.name}
                      scope="col" 
                      className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      {itemField.display_name}
                    </th>
                  ))}
                  {editMode && (
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      操作
                    </th>
                  )}
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {listData.map((item: any, itemIndex: number) => (
                  <tr key={itemIndex}>
                    {field.items!.fields!.map(itemField => (
                      <td key={itemField.name} className="px-6 py-4 whitespace-nowrap">
                        {editMode ? (
                          <input
                            type="text"
                            value={item[itemField.name] || ''}
                            onChange={(e) => updateListItemProperty(field.name, itemIndex, itemField.name, e.target.value)}
                            className="w-full p-1 border border-gray-300 rounded"
                            onFocus={() => onHighlightCell(field.name, itemIndex, itemField.name)}
                          />
                        ) : (
                          <div 
                            className="text-sm text-gray-900 cursor-pointer hover:bg-blue-50 p-1 rounded"
                            onClick={() => onHighlightCell(field.name, itemIndex, itemField.name)}
                          >
                            {item[itemField.name] || ''}
                          </div>
                        )}
                      </td>
                    ))}
                    {editMode && (
                      <td className="px-6 py-4 whitespace-nowrap">
                        <button
                          type="button"
                          onClick={() => {
                            const updatedList = [...listData];
                            updatedList.splice(itemIndex, 1);
                            updateFieldValue(field.name, updatedList);
                          }}
                          className="text-red-600 hover:text-red-900"
                        >
                          削除
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          
          {editMode && (
            <button
              type="button"
              onClick={() => {
                const newItem: Record<string, string> = {};
                field.items!.fields!.forEach(itemField => {
                  newItem[itemField.name] = '';
                });
                updateFieldValue(field.name, [...listData, newItem]);
              }}
              className="mt-2 text-blue-600 hover:text-blue-800"
            >
              + 行を追加
            </button>
          )}
        </div>
      );
    }
    
    // 単純なリストの場合
    return (
      <div key={field.name} className="mb-6">
        <h3 className="text-lg font-medium mb-2">{field.display_name}</h3>
        <ul className="list-disc pl-5">
          {listData.map((item: any, itemIndex: number) => (
            <li key={itemIndex} className="mb-2">
              {editMode ? (
                <input
                  type="text"
                  value={item || ''}
                  onChange={(e) => updateListItem(field.name, itemIndex, e.target.value)}
                  className="w-full p-1 border border-gray-300 rounded"
                />
              ) : (
                <div className="p-1">{item || ''}</div>
              )}
            </li>
          ))}
        </ul>
        
        {editMode && (
          <button
            type="button"
            onClick={() => {
              updateFieldValue(field.name, [...listData, '']);
            }}
            className="mt-2 text-blue-600 hover:text-blue-800"
          >
            + 項目を追加
          </button>
        )}
      </div>
    );
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold">{appDisplayName}の抽出結果</h2>
        <div className="flex space-x-2">
          {editMode ? (
            <>
              <button
                onClick={cancelEdit}
                className="px-4 py-2 rounded bg-gray-500 hover:bg-gray-600 text-white"
              >
                キャンセル
              </button>
              <button
                onClick={toggleEditMode}
                className="px-4 py-2 rounded bg-green-500 hover:bg-green-600 text-white"
              >
                保存
              </button>
            </>
          ) : (
            <>
              <button
                onClick={toggleEditMode}
                className="px-4 py-2 rounded bg-blue-500 hover:bg-blue-600 text-white"
              >
                編集
              </button>
              {onRunAgent && (
                <>
                  <button
                    onClick={handleShowTools}
                    className="px-4 py-2 rounded bg-gray-500 hover:bg-gray-600 text-white"
                  >
                    登録ツール一覧
                  </button>
                  <button
                    onClick={handleRunAgent}
                    disabled={agentStatus === 'running'}
                    className={`px-4 py-2 rounded text-white ${
                      agentStatus === 'running'
                        ? 'bg-gray-400 cursor-not-allowed'
                        : 'bg-purple-500 hover:bg-purple-600'
                    }`}
                  >
                    {agentStatus === 'running' ? '検証中...' : 'エージェントで検証'}
                  </button>
                </>
              )}
            </>
          )}
        </div>
      </div>
      
      <div className="space-y-4">
        {fields.map(field => renderField(field))}
      </div>

      {showToolsModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full max-h-[80vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold">登録ツール一覧</h2>
              <button
                onClick={() => setShowToolsModal(false)}
                className="text-gray-500 hover:text-gray-700"
              >
                ✕
              </button>
            </div>
            <div className="space-y-3">
              {tools.map((tool, index) => (
                <div key={index} className="p-3 border border-gray-200 rounded">
                  <div className="font-semibold text-gray-800">{tool.name}</div>
                  <div className="text-sm text-gray-600 mt-1">{tool.description}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ExtractedInfoDisplay;
