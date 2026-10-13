import React, { useEffect, useState } from "react";
import { api } from "../services/api";

const CATEGORIES = [
  "all",
  "preference",
  "personal",
  "professional",
  "project",
  "learning",
  "workflow",
  "technical",
  "goal",
  "other",
];

const CATEGORY_COLORS = {
  preference: "#00e5ff",
  personal: "#ff77a8",
  professional: "#00ff88",
  project: "#a78bfa",
  learning: "#38bdf8",
  workflow: "#fbbf24",
  technical: "#f472b6",
  goal: "#34d399",
  other: "#94a3b8",
};

export default function MemoryModal({ isOpen, onClose }) {
  const [memories, setMemories] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("all");

  // Add / Edit state
  const [showAddForm, setShowAddForm] = useState(false);
  const [newContent, setNewContent] = useState("");
  const [newCategory, setNewCategory] = useState("preference");
  const [newImportance, setNewImportance] = useState(0.8);

  const [editingId, setEditingId] = useState(null);
  const [editContent, setEditContent] = useState("");
  const [editCategory, setEditCategory] = useState("preference");
  const [editImportance, setEditImportance] = useState(0.8);

  const [confirmClear, setConfirmClear] = useState(false);

  useEffect(() => {
    if (isOpen) {
      loadMemories();
    }
  }, [isOpen, selectedCategory]);

  const loadMemories = async () => {
    setLoading(true);
    try {
      const cat = selectedCategory === "all" ? null : selectedCategory;
      const res = await api.getMemories(cat);
      setMemories(res.memories || []);
    } catch (err) {
      console.error("Failed to load memories:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) {
      loadMemories();
      return;
    }
    setLoading(true);
    try {
      const cat = selectedCategory === "all" ? null : selectedCategory;
      const res = await api.searchMemories(searchQuery.trim(), cat);
      setMemories(res.memories || []);
    } catch (err) {
      console.error("Search failed:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!newContent.trim()) return;
    try {
      await api.createMemory(newContent.trim(), newCategory, parseFloat(newImportance));
      setNewContent("");
      setShowAddForm(false);
      loadMemories();
    } catch (err) {
      alert(`Error creating memory: ${err.message}`);
    }
  };

  const handleStartEdit = (m) => {
    setEditingId(m.id);
    setEditContent(m.content);
    setEditCategory(m.category || "preference");
    setEditImportance(m.importance ?? 0.8);
  };

  const handleSaveEdit = async (id) => {
    try {
      await api.updateMemory(id, {
        content: editContent.trim(),
        category: editCategory,
        importance: parseFloat(editImportance),
      });
      setEditingId(null);
      loadMemories();
    } catch (err) {
      alert(`Error updating memory: ${err.message}`);
    }
  };

  const handleDelete = async (id) => {
    try {
      await api.deleteMemory(id);
      loadMemories();
    } catch (err) {
      alert(`Error deleting memory: ${err.message}`);
    }
  };

  const handleClearAll = async () => {
    try {
      await api.clearMemories();
      setConfirmClear(false);
      loadMemories();
    } catch (err) {
      alert(`Error clearing memories: ${err.message}`);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-content"
        style={{ maxWidth: "800px", width: "94%" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-header">
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div className="hud-arc-reactor" style={{ width: "24px", height: "24px" }}>
              <div className="hud-arc-inner" style={{ width: "10px", height: "10px" }}></div>
            </div>
            <div className="modal-title">PERSISTENT LONG-TERM MEMORY HUD</div>
          </div>
          <button className="modal-close-btn" onClick={onClose}>&times;</button>
        </div>

        <div className="modal-body" style={{ gap: "14px", maxHeight: "78vh" }}>
          {/* Controls Bar: Search & Action buttons */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: "10px", alignItems: "center" }}>
            <form onSubmit={handleSearch} style={{ display: "flex", flex: 1, minWidth: "240px", gap: "8px" }}>
              <input
                type="text"
                placeholder="Search memories by keyword..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  flex: 1,
                  background: "rgba(0, 0, 0, 0.5)",
                  border: "1px solid var(--cyan-border)",
                  borderRadius: "6px",
                  padding: "8px 12px",
                  color: "#fff",
                  fontSize: "0.85rem",
                  outline: "none",
                }}
              />
              <button type="submit" className="btn-hud">
                SEARCH
              </button>
            </form>

            <button
              className="btn-hud"
              onClick={() => setShowAddForm(!showAddForm)}
              style={{ borderColor: "var(--accent-green)", color: "var(--accent-green)" }}
            >
              {showAddForm ? "CANCEL" : "+ ADD MEMORY"}
            </button>

            <button
              className="btn-hud"
              onClick={() => setConfirmClear(true)}
              style={{ borderColor: "var(--accent-red)", color: "var(--accent-red)" }}
            >
              CLEAR ALL
            </button>
          </div>

          {/* Confirm Clear All Overlay */}
          {confirmClear && (
            <div
              style={{
                background: "rgba(255, 51, 102, 0.15)",
                border: "1px solid var(--accent-red)",
                padding: "12px",
                borderRadius: "8px",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <span style={{ color: "#ff8899", fontSize: "0.85rem" }}>
                ⚠️ Are you sure you want to permanently delete ALL persistent memories?
              </span>
              <div style={{ display: "flex", gap: "8px" }}>
                <button
                  className="btn-hud"
                  style={{ background: "var(--accent-red)", color: "#fff" }}
                  onClick={handleClearAll}
                >
                  YES, CLEAR ALL
                </button>
                <button className="btn-hud" onClick={() => setConfirmClear(false)}>
                  CANCEL
                </button>
              </div>
            </div>
          )}

          {/* Add Memory Form */}
          {showAddForm && (
            <form
              onSubmit={handleCreate}
              style={{
                background: "rgba(0, 229, 255, 0.05)",
                border: "1px dashed var(--cyan-primary)",
                borderRadius: "8px",
                padding: "14px",
                display: "flex",
                flexDirection: "column",
                gap: "10px",
              }}
            >
              <div style={{ color: "var(--cyan-primary)", fontFamily: "var(--font-hud)", fontSize: "0.8rem" }}>
                RECORD NEW PERSISTENT MEMORY
              </div>
              <textarea
                placeholder="Enter user preference, project detail, or durable fact..."
                value={newContent}
                onChange={(e) => setNewContent(e.target.value)}
                rows={2}
                required
                style={{
                  background: "rgba(0, 0, 0, 0.6)",
                  border: "1px solid var(--cyan-dim)",
                  borderRadius: "6px",
                  padding: "8px",
                  color: "#fff",
                  fontSize: "0.85rem",
                  resize: "vertical",
                }}
              />
              <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", alignItems: "center" }}>
                <label style={{ fontSize: "0.78rem", color: "var(--text-secondary)" }}>
                  Category:
                  <select
                    value={newCategory}
                    onChange={(e) => setNewCategory(e.target.value)}
                    style={{
                      marginLeft: "6px",
                      background: "#0d1527",
                      color: "#fff",
                      border: "1px solid var(--cyan-dim)",
                      padding: "4px 8px",
                      borderRadius: "4px",
                    }}
                  >
                    {CATEGORIES.filter((c) => c !== "all").map((cat) => (
                      <option key={cat} value={cat}>
                        {cat.toUpperCase()}
                      </option>
                    ))}
                  </select>
                </label>

                <label style={{ fontSize: "0.78rem", color: "var(--text-secondary)" }}>
                  Importance ({newImportance}):
                  <input
                    type="range"
                    min="0.1"
                    max="1.0"
                    step="0.1"
                    value={newImportance}
                    onChange={(e) => setNewImportance(e.target.value)}
                    style={{ marginLeft: "8px", verticalAlign: "middle" }}
                  />
                </label>

                <button type="submit" className="btn-hud" style={{ marginLeft: "auto" }}>
                  SAVE TO MEMORY STORE
                </button>
              </div>
            </form>
          )}

          {/* Category Tabs */}
          <div style={{ display: "flex", gap: "6px", overflowX: "auto", paddingBottom: "4px" }}>
            {CATEGORIES.map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                style={{
                  background: selectedCategory === cat ? "rgba(0, 229, 255, 0.2)" : "rgba(0, 0, 0, 0.4)",
                  border: `1px solid ${selectedCategory === cat ? "var(--cyan-primary)" : "rgba(255, 255, 255, 0.08)"}`,
                  color: selectedCategory === cat ? "var(--cyan-primary)" : "var(--text-secondary)",
                  padding: "4px 10px",
                  borderRadius: "14px",
                  fontSize: "0.72rem",
                  cursor: "pointer",
                  whiteSpace: "nowrap",
                  fontFamily: "var(--font-hud)",
                }}
              >
                {cat.toUpperCase()}
              </button>
            ))}
          </div>

          {/* Memories List */}
          <div style={{ display: "flex", flexDirection: "column", gap: "10px", overflowY: "auto" }}>
            {loading ? (
              <div style={{ textAlign: "center", color: "var(--cyan-primary)", padding: "20px" }}>
                SCANNING LOCAL MEMORY MATRICES...
              </div>
            ) : memories.length === 0 ? (
              <div style={{ textAlign: "center", color: "var(--text-muted)", padding: "24px" }}>
                No long-term memories found in this view.
              </div>
            ) : (
              memories.map((m) => {
                const isEditing = editingId === m.id;
                const catColor = CATEGORY_COLORS[m.category] || "#94a3b8";

                return (
                  <div
                    key={m.id}
                    style={{
                      background: "rgba(10, 18, 36, 0.7)",
                      border: "1px solid rgba(0, 229, 255, 0.18)",
                      borderRadius: "8px",
                      padding: "12px 14px",
                      display: "flex",
                      flexDirection: "column",
                      gap: "8px",
                      transition: "border-color 0.2s",
                    }}
                  >
                    {isEditing ? (
                      <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                        <textarea
                          value={editContent}
                          onChange={(e) => setEditContent(e.target.value)}
                          rows={2}
                          style={{
                            background: "#080d1a",
                            border: "1px solid var(--cyan-primary)",
                            borderRadius: "4px",
                            padding: "6px",
                            color: "#fff",
                            fontSize: "0.85rem",
                          }}
                        />
                        <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                          <select
                            value={editCategory}
                            onChange={(e) => setEditCategory(e.target.value)}
                            style={{
                              background: "#0d1527",
                              color: "#fff",
                              border: "1px solid var(--cyan-dim)",
                              padding: "4px 8px",
                              borderRadius: "4px",
                              fontSize: "0.75rem",
                            }}
                          >
                            {CATEGORIES.filter((c) => c !== "all").map((cat) => (
                              <option key={cat} value={cat}>
                                {cat.toUpperCase()}
                              </option>
                            ))}
                          </select>

                          <label style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                            Importance: {editImportance}
                            <input
                              type="range"
                              min="0.1"
                              max="1.0"
                              step="0.1"
                              value={editImportance}
                              onChange={(e) => setEditImportance(e.target.value)}
                              style={{ marginLeft: "6px", verticalAlign: "middle" }}
                            />
                          </label>

                          <div style={{ marginLeft: "auto", display: "flex", gap: "6px" }}>
                            <button
                              className="btn-hud"
                              style={{ color: "var(--accent-green)", borderColor: "var(--accent-green)" }}
                              onClick={() => handleSaveEdit(m.id)}
                            >
                              SAVE
                            </button>
                            <button className="btn-hud" onClick={() => setEditingId(null)}>
                              CANCEL
                            </button>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                          <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                            <span
                              style={{
                                background: `${catColor}22`,
                                border: `1px solid ${catColor}`,
                                color: catColor,
                                padding: "2px 8px",
                                borderRadius: "10px",
                                fontSize: "0.68rem",
                                fontWeight: "600",
                                fontFamily: "var(--font-hud)",
                              }}
                            >
                              {m.category?.toUpperCase() || "OTHER"}
                            </span>
                            <span
                              style={{
                                color: "var(--text-muted)",
                                fontSize: "0.72rem",
                                fontFamily: "var(--font-mono)",
                              }}
                            >
                              Imp: {(m.importance * 100).toFixed(0)}%
                            </span>
                          </div>

                          <div style={{ display: "flex", gap: "6px" }}>
                            <button
                              className="btn-hud"
                              style={{ padding: "2px 8px", fontSize: "0.68rem" }}
                              onClick={() => handleStartEdit(m)}
                              title="Edit memory"
                            >
                              EDIT
                            </button>
                            <button
                              className="btn-hud"
                              style={{
                                padding: "2px 8px",
                                fontSize: "0.68rem",
                                borderColor: "var(--accent-red)",
                                color: "var(--accent-red)",
                              }}
                              onClick={() => handleDelete(m.id)}
                              title="Delete memory"
                            >
                              &times;
                            </button>
                          </div>
                        </div>

                        <div style={{ color: "var(--text-primary)", fontSize: "0.9rem", lineHeight: "1.4" }}>
                          {m.content}
                        </div>

                        <div
                          style={{
                            display: "flex",
                            justifyContent: "space-between",
                            fontSize: "0.68rem",
                            color: "var(--text-muted)",
                            fontFamily: "var(--font-mono)",
                            borderTop: "1px dashed rgba(255, 255, 255, 0.05)",
                            paddingTop: "6px",
                          }}
                        >
                          <span>Created: {new Date(m.created_at).toLocaleDateString()}</span>
                          <span>Source: {m.source || "conversation"}</span>
                          <span>Access: {m.access_count ?? 0}</span>
                        </div>
                      </>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
