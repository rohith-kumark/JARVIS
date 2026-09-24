import React, { useState, useEffect } from 'react';
import { X, Wrench, Shield, CheckCircle, AlertCircle, Play, ChevronDown, ChevronRight } from 'lucide-react';
import { apiClient } from '../api/client';

export function ToolRegistryModal({ isOpen, onClose }) {
  const [tools, setTools] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expandedTool, setExpandedTool] = useState(null);
  const [executionResult, setExecutionResult] = useState(null);
  const [executingToolName, setExecutingToolName] = useState(null);

  useEffect(() => {
    if (isOpen) {
      loadTools();
    }
  }, [isOpen]);

  const loadTools = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.getTools();
      setTools(data.tools || []);
    } catch (err) {
      setError(err.message || 'Failed to fetch registered tools');
    } finally {
      setLoading(false);
    }
  };

  const handleTestExecute = async (toolName) => {
    setExecutingToolName(toolName);
    setExecutionResult(null);
    try {
      const res = await apiClient.executeTool(toolName, {}, 'admin');
      setExecutionResult({ tool: toolName, ...res });
    } catch (err) {
      setExecutionResult({
        tool: toolName,
        success: false,
        error: err.message,
      });
    } finally {
      setExecutingToolName(null);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-container" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title">
            <Wrench size={18} className="text-cyan" />
            <span>Central Tool Registry</span>
            <span className="modal-badge">{tools.length} Tools Active</span>
          </div>
          <button className="icon-btn" onClick={onClose}>
            <X size={16} />
          </button>
        </div>

        <div className="modal-body">
          <p className="modal-description">
            Every external action in JARVIS is governed by a registered, permission-checked tool.
            Tools declare their JSON schema, execution boundary, and security clearance.
          </p>

          {loading ? (
            <div className="modal-state">Querying tool registry...</div>
          ) : error ? (
            <div className="telemetry-error">{error}</div>
          ) : (
            <div className="tool-list">
              {tools.map((tool) => {
                const isExpanded = expandedTool === tool.name;
                return (
                  <div key={tool.name} className="tool-card">
                    <div className="tool-card-main">
                      <div className="tool-card-header">
                        <span className="tool-name font-mono">{tool.name}</span>
                        <span className={`permission-badge perm-${tool.permission_level}`}>
                          <Shield size={10} />
                          {tool.permission_level.toUpperCase()}
                        </span>
                      </div>
                      <p className="tool-desc">{tool.description}</p>
                    </div>

                    <div className="tool-card-footer">
                      <button
                        className="tool-expand-btn"
                        onClick={() => setExpandedTool(isExpanded ? null : tool.name)}
                      >
                        {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                        <span>Parameters Schema</span>
                      </button>

                      <button
                        className="btn-test-run"
                        onClick={() => handleTestExecute(tool.name)}
                        disabled={executingToolName === tool.name}
                      >
                        <Play size={12} />
                        <span>{executingToolName === tool.name ? 'Running...' : 'Execute'}</span>
                      </button>
                    </div>

                    {isExpanded && (
                      <div className="tool-schema-drawer">
                        <pre className="schema-pre">
                          {JSON.stringify(tool.parameters, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {executionResult && (
            <div className="test-result-box">
              <div className="test-result-header">
                <span className="test-result-title">
                  Execution Output for <code className="font-mono">{executionResult.tool}</code>
                </span>
                <span className={`test-status-pill ${executionResult.success ? 'pill-success' : 'pill-failure'}`}>
                  {executionResult.success ? 'SUCCESS' : 'FAILED'}
                </span>
              </div>
              <pre className="test-result-json">
                {JSON.stringify(executionResult, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default ToolRegistryModal;
