"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { CrossSessionDedup } from "./cross-session-dedup";
import {
  AlertCircle,
  AlertTriangle,
  Clock3,
  Compass,
  FolderPlus,
  MapPin,
  Play,
  Plus,
  RotateCcw,
  Settings,
  SlidersHorizontal,
  Sparkles,
  Trash2,
  Utensils,
  Coffee,
  Sunset,
  Moon,
  Camera,
  Tent,
  X,
  ChevronDown,
  KeyRound,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { useLanguage } from "@/lib/i18n/context";
import { ImportSessionModal } from "./import-session-modal";
import { threadsApi } from "./api";
import {
  keywordAnalysisResponseSchema,
  type ThreadsAccountItem,
  type ThreadsConfig,
  type ThreadsParameters,
} from "./types";
import styles from "./threads.module.css";

const CITIES = [
  "TP. Hồ Chí Minh",
  "Hà Nội",
  "Đà Lạt",
  "Đà Nẵng",
  "Vũng Tàu",
  "Nha Trang",
];

const CATEGORIES = [
  { id: "hidden_food", label: "Quán ăn ít người biết", icon: Utensils, hint: "Quán ngon núp hẻm, ẩm thực bản địa" },
  { id: "quiet_cafe", label: "Cafe yên tĩnh / làm việc", icon: Coffee, hint: "Không gian chill, bàn rộng, ít ồn" },
  { id: "sunset_view", label: "Ngắm hoàng hôn / view đẹp", icon: Sunset, hint: "Bờ sông, rooftop, ban công thoáng" },
  { id: "night_life", label: "Ăn đêm & dạo phố", icon: Moon, hint: "Mở khuya sau 22h, phố ẩm thực đêm" },
  { id: "check_in", label: "Điểm chụp ảnh / check-in độc lạ", icon: Camera, hint: "Cổ kính, phong cách vintage, kiến trúc đẹp" },
  { id: "nature_camp", label: "Dã ngoại & thiên nhiên", icon: Tent, hint: "Công viên xanh, bãi cỏ ngắm cảnh, cắm trại" },
];

const INITIAL_GROUPS = [
  {
    category: "Ẩm thực & Quán ngon",
    keywords: [
      "quán ăn ít người biết tphcm",
      "quán ốc ngon sài gòn",
      "ăn đêm sài gòn núp hẻm",
    ],
  },
  {
    category: "Cafe & Không gian chill",
    keywords: [
      "cafe chill yên tĩnh tphcm",
      "cafe sân vườn view thoáng sài gòn",
    ],
  },
  {
    category: "Check-in & Điểm đến",
    keywords: [
      "địa điểm chụp ảnh đẹp tphcm",
      "chỗ đi chơi cuối tuần sài gòn",
    ],
  },
];

const POST_LIMIT_OPTIONS = [25, 50, 75, 100];
const COMMENT_LIMIT_OPTIONS = [25, 50, 100];

export function ThreadsTravelForm({
  config,
  parameters,
  busy,
  error,
  isQueuing = false,
  onChange,
  onReset,
  onSubmit,
  onRefreshConfig,
}: {
  config: ThreadsConfig | null;
  parameters: ThreadsParameters;
  busy: boolean;
  error: string | null;
  isQueuing?: boolean;
  onChange: (value: Partial<ThreadsParameters>) => void;
  onReset: () => void;
  onSubmit: (prompt: string, selectedKeywords: string[]) => void;
  onRefreshConfig?: () => void;
}) {
  const { t, language } = useLanguage();
  const ready = config?.enabled && config.accounts_ready;
  const [showImportModal, setShowImportModal] = useState(false);
  const [accounts, setAccounts] = useState<ThreadsAccountItem[]>([]);

  useEffect(() => {
    let ignore = false;
    fetch("/api/threads/accounts")
      .then((res) => res.json())
      .then((data) => {
        if (!ignore && Array.isArray(data.accounts)) {
          setAccounts(data.accounts);
        }
      })
      .catch(() => {});
    return () => {
      ignore = true;
    };
  }, [config]);

  const expiredAccounts = accounts.filter((a) => a.has_session && a.is_expired);

  // Prompt state
  const [selectedCity, setSelectedCity] = useState("TP. Hồ Chí Minh");
  const [selectedCategory, setSelectedCategory] = useState("hidden_food");
  const [prompt, setPrompt] = useState(
    "Tìm các quán ăn ngon núp hẻm, quán ốc, lẩu ít người biết quanh TP. Hồ Chí Minh và cafe view chill"
  );

  // Grouped keywords state
  const [groups, setGroups] = useState<Array<{ category: string; keywords: string[] }>>(INITIAL_GROUPS);
  const [selectedKeywords, setSelectedKeywords] = useState<Set<string>>(
    () => new Set(INITIAL_GROUPS.flatMap((g) => g.keywords))
  );
  const [newKeywordInputs, setNewKeywordInputs] = useState<Record<number, string>>({});
  const [newGroupTitle, setNewGroupTitle] = useState("");
  const [showAddGroup, setShowAddGroup] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const isUnlimitedComments = parameters.max_comments_per_post <= 0;
  const activeFilterLevel =
    !parameters.pre_filter || parameters.pre_filter_strictness === "none"
      ? "none"
      : parameters.pre_filter_strictness === "medium"
      ? "medium"
      : "high";

  // AI Keyword Analysis
  async function handleAnalyzeKeywords() {
    if (!prompt.trim()) return;
    setIsAnalyzing(true);
    setAnalysisError(null);
    try {
      const response = await threadsApi(
        "/keywords",
        keywordAnalysisResponseSchema,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: prompt.trim(), count: 5 }),
        }
      );

      if (response.groups && response.groups.length > 0) {
        setGroups(response.groups);
        const allKeywords = response.groups.flatMap((g) => g.keywords);
        setSelectedKeywords(new Set(allKeywords));
      } else if (response.keywords && response.keywords.length > 0) {
        setGroups([{ category: "Từ khóa gợi ý", keywords: response.keywords }]);
        setSelectedKeywords(new Set(response.keywords));
      }
    } catch (err) {
      setAnalysisError(
        err instanceof Error
          ? err.message
          : "Không thể phân tích keyword. Vui lòng thử lại."
      );
    } finally {
      setIsAnalyzing(false);
    }
  }

  function toggleKeyword(kw: string) {
    setSelectedKeywords((prev) => {
      const next = new Set(prev);
      if (next.has(kw)) next.delete(kw);
      else next.add(kw);
      return next;
    });
  }

  function toggleGroupAll(groupIndex: number) {
    const group = groups[groupIndex];
    if (!group) return;
    const allSelected = group.keywords.every((k) => selectedKeywords.has(k));
    setSelectedKeywords((prev) => {
      const next = new Set(prev);
      for (const k of group.keywords) {
        if (allSelected) next.delete(k);
        else next.add(k);
      }
      return next;
    });
  }

  function addKeywordToGroup(groupIndex: number) {
    const input = (newKeywordInputs[groupIndex] || "").trim();
    if (!input) return;
    setGroups((prev) =>
      prev.map((g, idx) => {
        if (idx !== groupIndex) return g;
        if (g.keywords.includes(input)) return g;
        return { ...g, keywords: [...g.keywords, input] };
      })
    );
    setSelectedKeywords((prev) => new Set(prev).add(input));
    setNewKeywordInputs((prev) => ({ ...prev, [groupIndex]: "" }));
  }

  function removeKeywordFromGroup(groupIndex: number, kw: string) {
    setGroups((prev) =>
      prev.map((g, idx) => {
        if (idx !== groupIndex) return g;
        return { ...g, keywords: g.keywords.filter((k) => k !== kw) };
      })
    );
    setSelectedKeywords((prev) => {
      const next = new Set(prev);
      next.delete(kw);
      return next;
    });
  }

  function handleAddNewGroup() {
    const title = newGroupTitle.trim();
    if (!title) return;
    setGroups((prev) => [...prev, { category: title, keywords: [] }]);
    setNewGroupTitle("");
    setShowAddGroup(false);
  }

  function handleRemoveGroup(groupIndex: number) {
    const group = groups[groupIndex];
    if (!group) return;
    setSelectedKeywords((prev) => {
      const next = new Set(prev);
      for (const k of group.keywords) next.delete(k);
      return next;
    });
    setGroups((prev) => prev.filter((_, idx) => idx !== groupIndex));
  }

  function handleApplyCity(city: string) {
    setSelectedCity(city);
    setPrompt(`Tìm các quán ăn ngon, quán cafe yên tĩnh và địa điểm du lịch đẹp ít người biết tại ${city}`);
  }

  function handleApplyCategory(cat: typeof CATEGORIES[0]) {
    setSelectedCategory(cat.id);
    setPrompt(`Tìm các ${cat.label.toLowerCase()} quanh ${selectedCity}, ${cat.hint}`);
  }

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    onSubmit(prompt.trim(), Array.from(selectedKeywords));
  }

  const selectedCount = selectedKeywords.size;
  const isDiscoveryPlanning = parameters.discovery_mode === "evidence_poi" && parameters.query_planning;

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      {/* Title & Reset */}
      <div className={styles.sectionTitle}>
        <div>
          <Compass size={17} />
          <h2>{t("threads.configTitle")} — {t("threads.tabTravel")}</h2>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <button
            type="button"
            className={styles.textButton}
            onClick={() => setShowImportModal(true)}
            title="Import or update Threads session"
          >
            <KeyRound size={13} />
            Session
          </button>
          <button
            type="button"
            className={styles.textButton}
            onClick={() => {
              onReset();
              setGroups(INITIAL_GROUPS);
              setSelectedKeywords(new Set(INITIAL_GROUPS.flatMap((g) => g.keywords)));
              setPrompt("Tìm các quán ăn ngon núp hẻm, quán ốc, lẩu ít người biết quanh TP. Hồ Chí Minh và cafe view chill");
            }}
          >
            <RotateCcw size={13} />
            {t("threads.reset")}
          </button>
        </div>
      </div>

      {/* Step 1: City quick filter */}
      <div className={styles.travelSection}>
        <span className={styles.travelSectionLabel}>
          <MapPin size={14} />
          {t("threads.travelCityLabel")}
        </span>
        <div className={styles.chipsRow}>
          {CITIES.map((city) => (
            <button
              key={city}
              type="button"
              className={styles.chipButton}
              data-active={selectedCity === city}
              onClick={() => handleApplyCity(city)}
            >
              {city}
            </button>
          ))}
        </div>
      </div>

      {/* Step 2: Prompt Input & Category inspirations */}
      <label className={styles.field} htmlFor="travel-prompt">
        <div className={styles.travelSectionHeader}>
          <span>{t("threads.travelPromptLabel")}</span>
          <span className={styles.promptLengthHint}>{prompt.length} / 1000 ký tự</span>
        </div>
        <textarea
          id="travel-prompt"
          rows={3}
          maxLength={1000}
          required
          value={prompt}
          placeholder={t("threads.travelPromptPlaceholder")}
          onChange={(event) => setPrompt(event.target.value)}
        />
        <div className={styles.promptActionRow}>
          <div className={styles.categoryPills}>
            {CATEGORIES.map((cat) => {
              const Icon = cat.icon;
              return (
                <button
                  key={cat.id}
                  type="button"
                  className={styles.categoryMiniPill}
                  data-active={selectedCategory === cat.id}
                  onClick={() => handleApplyCategory(cat)}
                  title={cat.hint}
                >
                  <Icon size={12} />
                  <span>{cat.label}</span>
                </button>
              );
            })}
          </div>

          <Button
            type="button"
            variant="outline"
            className={styles.analyzeKeywordsBtn}
            onClick={handleAnalyzeKeywords}
            disabled={isAnalyzing || !prompt.trim() || busy}
          >
            <Sparkles size={14} className={isAnalyzing ? styles.rotateIcon : ""} />
            {isAnalyzing ? t("threads.analyzingKeywords") : t("threads.analyzeKeywordsBtn")}
          </Button>
        </div>

        {analysisError && (
          <div className={styles.analysisError} role="alert">
            <AlertCircle size={14} />
            <span>{analysisError}</span>
          </div>
        )}
      </label>

      {/* Step 3: Grouped Keywords Selection (Phân tích theo nhóm để tối ưu) */}
      <section className={styles.formSection}>
        <div className={styles.groupedKeywordsHeader}>
          <div>
            <h3 style={{ margin: 0 }}>
              <Compass size={15} />
              {t("threads.groupedKeywordsTitle")} ({groups.length} nhóm chủ đề)
            </h3>
            <small className={styles.hint}>{t("threads.groupedKeywordsDesc")}</small>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setShowAddGroup((v) => !v)}
          >
            <FolderPlus size={13} />
            {t("threads.addKeywordGroup")}
          </Button>
        </div>

        {showAddGroup && (
          <div className={styles.addGroupBar}>
            <input
              type="text"
              className={styles.addGroupInput}
              placeholder={t("threads.newGroupName")}
              value={newGroupTitle}
              onChange={(e) => setNewGroupTitle(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  handleAddNewGroup();
                }
              }}
            />
            <button
              type="button"
              className={styles.addGroupBtn}
              onClick={handleAddNewGroup}
              disabled={!newGroupTitle.trim()}
            >
              <Plus size={13} />
              Thêm nhóm
            </button>
          </div>
        )}

        {/* Group Cards Grid */}
        <div className={styles.groupsGrid}>
          {groups.map((group, groupIdx) => {
            const allSelected =
              group.keywords.length > 0 &&
              group.keywords.every((k) => selectedKeywords.has(k));
            const selectedInGroupCount = group.keywords.filter((k) =>
              selectedKeywords.has(k)
            ).length;

            return (
              <div key={`${group.category}-${groupIdx}`} className={styles.groupCard}>
                <div className={styles.groupCardHeader}>
                  <div className={styles.groupCardTitle}>
                    <span>{group.category}</span>
                    <span className={styles.groupCountBadge}>
                      {selectedInGroupCount}/{group.keywords.length}
                    </span>
                  </div>

                  <div className={styles.groupActions}>
                    <button
                      type="button"
                      className={styles.groupToggleAllBtn}
                      onClick={() => toggleGroupAll(groupIdx)}
                    >
                      {allSelected
                        ? t("threads.deselectAllInGroup")
                        : t("threads.selectAllInGroup")}
                    </button>
                    {groups.length > 1 && (
                      <button
                        type="button"
                        className={styles.groupDeleteBtn}
                        onClick={() => handleRemoveGroup(groupIdx)}
                        title={t("threads.removeGroup")}
                      >
                        <Trash2 size={13} />
                      </button>
                    )}
                  </div>
                </div>

                <div className={styles.groupKeywordsList}>
                  {group.keywords.map((kw) => {
                    const isChecked = selectedKeywords.has(kw);
                    return (
                      <label
                        key={kw}
                        className={styles.groupKeywordItem}
                        data-checked={isChecked}
                      >
                        <input
                          type="checkbox"
                          className={styles.groupKeywordCheckbox}
                          checked={isChecked}
                          onChange={() => toggleKeyword(kw)}
                        />
                        <span>{kw}</span>
                        <span className={styles.dualModeTag}>Top + Mới</span>
                        <button
                          type="button"
                          className={styles.groupKeywordRemove}
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            removeKeywordFromGroup(groupIdx, kw);
                          }}
                          title={`Xóa ${kw}`}
                        >
                          <X size={12} />
                        </button>
                      </label>
                    );
                  })}
                </div>

                <div className={styles.groupInlineAddRow}>
                  <input
                    type="text"
                    className={styles.groupInlineAddInput}
                    placeholder={t("threads.addKeywordToGroup")}
                    value={newKeywordInputs[groupIdx] || ""}
                    onChange={(e) =>
                      setNewKeywordInputs((prev) => ({
                        ...prev,
                        [groupIdx]: e.target.value,
                      }))
                    }
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        addKeywordToGroup(groupIdx);
                      }
                    }}
                  />
                  <button
                    type="button"
                    className={styles.groupInlineAddBtn}
                    onClick={() => addKeywordToGroup(groupIdx)}
                    disabled={!(newKeywordInputs[groupIdx] || "").trim()}
                  >
                    <Plus size={13} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        {/* Selected Summary */}
        <div className={styles.selectedSummaryRow}>
          <span>
            {t("threads.selectedKeywordsSummary")}:{" "}
            <strong className={styles.selectedCountHighlight}>
              {selectedCount} từ khóa
            </strong>
          </span>
        </div>
        <CrossSessionDedup enabled={parameters.check_duplicate}
          onChange={(check_duplicate) => onChange({ check_duplicate })} />
      </section>

      {/* Step 4: Search Order & Posts per Keyword */}
      <section className={styles.formSection} aria-labelledby="travel-search-settings-label">
        <h3 id="travel-search-settings-label">
          <SlidersHorizontal size={15} />
          {t("threads.searchOrder")} &amp; {t("threads.postsPerKeyword")}
        </h3>

        <div className={styles.segmentedGroup}>
          <span>{t("threads.searchOrder")}</span>
          <div className={styles.segmentedControl}>
            <button
              type="button"
              className={styles.segmentedButton}
              data-active={parameters.search_type === "recent"}
              onClick={() => onChange({ search_type: "recent" })}
            >
              {t("threads.recent")}
            </button>
            <button
              type="button"
              className={styles.segmentedButton}
              data-active={parameters.search_type === "top"}
              onClick={() => onChange({ search_type: "top" })}
            >
              {t("threads.top")}
            </button>
            <button
              type="button"
              className={styles.segmentedButton}
              data-active={parameters.search_type === "both"}
              onClick={() => onChange({ search_type: "both" })}
            >
              {t("threads.searchBoth")}
            </button>
          </div>
        </div>

        <div className={styles.segmentedGroup}>
          <span>{t("threads.postsPerKeyword")}</span>
          <div className={styles.segmentedGrid}>
            {POST_LIMIT_OPTIONS.map((count) => (
              <button
                key={count}
                type="button"
                className={styles.segmentedGridButton}
                data-active={parameters.max_posts_per_keyword === count}
                onClick={() => onChange({ max_posts_per_keyword: count })}
              >
                {count}
              </button>
            ))}
          </div>
          <small className={styles.hint}>{t("threads.postsPerKeywordHint")}</small>
        </div>
      </section>

      {/* Step 5: Comment Collection Section */}
      <section className={styles.formSection} aria-labelledby="travel-comments-label">
        <label className={styles.toggle}>
          <input
            type="checkbox"
            checked={parameters.include_comments}
            onChange={(event) => onChange({ include_comments: event.target.checked })}
          />
          <span>
            <strong id="travel-comments-label">{t("threads.commentsLabel")}</strong>
            <small>{t("threads.commentsDesc")}</small>
          </span>
        </label>

        {parameters.include_comments && (
          <fieldset className={styles.commentSettings}>
            <legend className="sr-only">Comment collection limits</legend>

            <div className={styles.segmentedGroup}>
              <span>{t("threads.commentsLimit")}</span>
              <div className={styles.segmentedGrid}>
                {COMMENT_LIMIT_OPTIONS.map((count) => (
                  <button
                    key={count}
                    type="button"
                    className={styles.segmentedGridButton}
                    data-active={parameters.max_comments_per_post === count}
                    onClick={() => onChange({ max_comments_per_post: count })}
                  >
                    {count}
                  </button>
                ))}
                <button
                  type="button"
                  className={styles.segmentedGridButton}
                  data-active={isUnlimitedComments}
                  onClick={() => onChange({ max_comments_per_post: -1 })}
                  title={t("threads.commentsAll")}
                  aria-label={t("threads.commentsAll")}
                >
                  ♾️
                </button>
              </div>
            </div>

            {isUnlimitedComments && (
              <div className={styles.unlimitedNotice}>
                <Sparkles size={15} />
                <span>{t("threads.commentsAllNotice")}</span>
              </div>
            )}
          </fieldset>
        )}
      </section>

      {/* Step 6: AI Assistance Section */}
      <section className={styles.formSection} aria-labelledby="travel-ai-label">
        <h3 id="travel-ai-label">
          <Sparkles size={15} />
          {t("threads.aiTitle")}
        </h3>
        {!config?.ai_available && config && <p className={styles.hint}>{t("threads.aiUnavailable")}</p>}

        <div className={styles.segmentedGroup}>
          <span>{t("threads.preFilterStrictness")}</span>
          <div className={styles.segmentedControl}>
            <button
              type="button"
              className={styles.segmentedButton}
              data-active={activeFilterLevel === "none"}
              onClick={() => onChange({ pre_filter: false, pre_filter_strictness: "none" })}
            >
              {t("threads.strictnessNone")}
            </button>
            <button
              type="button"
              className={styles.segmentedButton}
              disabled={!config?.ai_available}
              data-active={activeFilterLevel === "medium"}
              onClick={() => onChange({ pre_filter: true, pre_filter_strictness: "medium" })}
            >
              {t("threads.strictnessMedium")}
            </button>
            <button
              type="button"
              className={styles.segmentedButton}
              disabled={!config?.ai_available}
              data-active={activeFilterLevel === "high"}
              onClick={() => onChange({ pre_filter: true, pre_filter_strictness: "high" })}
            >
              {t("threads.strictnessHigh")}
            </button>
          </div>
          <small className={styles.hint}>
            {activeFilterLevel === "none"
              ? t("threads.strictnessNoneDesc")
              : activeFilterLevel === "medium"
              ? t("threads.strictnessMediumDesc")
              : t("threads.strictnessHighDesc")}
          </small>
        </div>
      </section>

      {/* Step 7: Advanced Settings Section */}
      <section className={styles.formSection} aria-labelledby="travel-advanced-label">
        <button
          type="button"
          id="travel-advanced-label"
          className={styles.fineTuneToggle}
          onClick={() => setShowAdvanced((prev) => !prev)}
          aria-expanded={showAdvanced}
        >
          <div>
            <SlidersHorizontal size={14} />
            <span>{showAdvanced ? t("threads.hideAdvancedSettings") : t("threads.advancedSettings")}</span>
          </div>
          <ChevronDown size={14} className={showAdvanced ? styles.rotate180 : undefined} />
        </button>

        {showAdvanced && (
          <div className={styles.fineTunePanel}>
            {/* Run Timeout */}
            <div className={styles.segmentedGroup}>
              <span>{t("threads.runTimeoutLabel")}</span>
              <div className={styles.segmentedGrid}>
                {[
                  { label: "30m", val: 1800 },
                  { label: "1h", val: 3600 },
                  { label: "2h", val: 7200 },
                  { label: t("threads.runTimeoutUnlimited"), val: -1 },
                ].map(({ label, val }) => (
                  <button
                    key={val}
                    type="button"
                    className={styles.segmentedGridButton}
                    data-active={parameters.run_timeout_seconds === val}
                    onClick={() => onChange(val === -1 ? { run_timeout_seconds: -1, search_timeout_seconds: -1 } : { run_timeout_seconds: val })}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <small className={styles.hint}>{t("threads.runTimeoutHint")}</small>
              {parameters.run_timeout_seconds === -1 && (
                <div className={styles.unlimitedNotice}>
                  <Sparkles size={15} />
                  <span>{t("threads.runTimeoutUnlimitedNotice")}</span>
                </div>
              )}
            </div>

            {/* Search Timeout */}
            <div className={styles.segmentedGroup}>
              <span>{t("threads.searchTimeoutLabel")}</span>
              <div className={styles.segmentedGrid}>
                {[
                  { label: "1m", val: 60 },
                  { label: "2m", val: 120 },
                  { label: "5m", val: 300 },
                  { label: "10m", val: 600 },
                  { label: t("threads.runTimeoutUnlimited"), val: -1 },
                ].map(({ label, val }) => (
                  <button
                    key={val}
                    type="button"
                    className={styles.segmentedGridButton}
                    data-active={parameters.search_timeout_seconds === val}
                    onClick={() => onChange({ search_timeout_seconds: val })}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <small className={styles.hint}>{t("threads.searchTimeoutHint")}</small>
            </div>

            {/* Posts with Comments limit & Min Replies */}
            {parameters.include_comments && (
              <>
                <div className={styles.segmentedGroup}>
                  <span>{t("threads.postsWithCommentsOption")}</span>
                  <div className={styles.segmentedControl}>
                    {[
                      { label: t("threads.postsWithCommentsAll"), val: -1 },
                      { label: "10", val: 10 },
                      { label: "25", val: 25 },
                      { label: "50", val: 50 },
                      { label: "100", val: 100 },
                    ].map(({ label, val }) => (
                      <button
                        key={val}
                        type="button"
                        className={styles.segmentedButton}
                        data-active={parameters.max_comment_posts === val}
                        onClick={() => onChange({ max_comment_posts: val })}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                  <small className={styles.hint}>{t("threads.maxCommentPostsHint")}</small>
                </div>

                <div className={styles.segmentedGroup}>
                  <span>{t("threads.minReplies")}</span>
                  <div className={styles.segmentedControl}>
                    {[
                      { label: "0", val: 0 },
                      { label: "≥ 2", val: 2 },
                      { label: "≥ 5", val: 5 },
                      { label: "≥ 10", val: 10 },
                    ].map(({ label, val }) => (
                      <button
                        key={val}
                        type="button"
                        className={styles.segmentedButton}
                        data-active={parameters.min_replies === val}
                        onClick={() => onChange({ min_replies: val })}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                  <small className={styles.hint}>{t("threads.minRepliesHint")}</small>
                </div>
              </>
            )}

            {/* Pacing Delays */}
            <div className={styles.segmentedGroup}>
              <span>{t("threads.delaysLabel")}</span>
              <div className={styles.segmentedControl}>
                <button
                  type="button"
                  className={styles.segmentedButton}
                  data-active={parameters.min_delay_seconds === 1 && parameters.max_delay_seconds === 2}
                  onClick={() => onChange({ min_delay_seconds: 1, max_delay_seconds: 2 })}
                >
                  {t("threads.delaysFast")}
                </button>
                <button
                  type="button"
                  className={styles.segmentedButton}
                  data-active={parameters.min_delay_seconds === 2 && parameters.max_delay_seconds === 4}
                  onClick={() => onChange({ min_delay_seconds: 2, max_delay_seconds: 4 })}
                >
                  {t("threads.delaysNormal")}
                </button>
                <button
                  type="button"
                  className={styles.segmentedButton}
                  data-active={parameters.min_delay_seconds === 4 && parameters.max_delay_seconds === 8}
                  onClick={() => onChange({ min_delay_seconds: 4, max_delay_seconds: 8 })}
                >
                  {t("threads.delaysSafe")}
                </button>
              </div>
              <small className={styles.hint}>{t("threads.delaysHint")}</small>
            </div>

            {/* Max Accounts */}
            <div className={styles.segmentedGroup}>
              <span>{t("threads.maxAccountsLabel")}</span>
              <div className={styles.segmentedControl}>
                {[
                  { label: `1 ${t("threads.accountUnit")}`, val: 1 },
                  { label: `2 ${t("threads.accountsUnit")}`, val: 2 },
                  { label: `3 ${t("threads.accountsUnit")}`, val: 3 },
                  { label: t("threads.maxAccountsAll"), val: -1 },
                ].map(({ label, val }) => (
                  <button
                    key={val}
                    type="button"
                    className={styles.segmentedButton}
                    data-active={parameters.max_accounts === val}
                    onClick={() => onChange({ max_accounts: val })}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <small className={styles.hint}>{t("threads.maxAccountsHint")}</small>
            </div>
          </div>
        )}
      </section>

      {expiredAccounts.length > 0 && (
        <div className={styles.notice} role="status" style={{ borderLeft: ready ? "4px solid #f59e0b" : "4px solid #ef4444" }}>
          <div className="flex items-start gap-2">
            <AlertTriangle className={`h-4 w-4 ${ready ? "text-amber-500" : "text-red-500"} shrink-0 mt-0.5`} />
            <div>
              <p style={{ margin: 0, fontWeight: 600, color: ready ? "#d97706" : "#ef4444" }}>
                {language === "vi" ? "Lưu ý phiên tài khoản" : "Session Notice"}
              </p>
              <p style={{ margin: "2px 0 8px 0", fontSize: "0.85rem" }}>
                {language === "vi"
                  ? ready
                    ? `Tài khoản (${expiredAccounts.map((a) => a.id).join(", ")}) có phiên đăng nhập đã hết hạn. Hệ thống sẽ tự động dùng các tài khoản đang hoạt động còn lại để cào dữ liệu.`
                    : `Tài khoản (${expiredAccounts.map((a) => a.id).join(", ")}) có phiên đăng nhập đã hết hạn. Vui lòng liên hệ Admin để cập nhật lại session JSON trong Cài đặt.`
                  : ready
                    ? `Session for account(s) ${expiredAccounts.map((a) => a.id).join(", ")} is expired. The system will automatically skip them and use the active accounts.`
                    : `Session for account(s) ${expiredAccounts.map((a) => a.id).join(", ")} has expired. Please ask an administrator to update the session JSON in Settings.`}
              </p>
              <Button variant="outline" size="sm" asChild className="gap-1.5 text-xs">
                <Link href="/settings/account">
                  <Settings size={13} />
                  {language === "vi" ? "Đi đến Cài đặt" : "Open Settings"}
                </Link>
              </Button>
            </div>
          </div>
        </div>
      )}

      {config && !ready && (
        <div className={styles.notice} role="status">
          <p style={{ margin: 0, marginBottom: "8px" }}>
            {language === "vi"
              ? "Thu thập Threads chưa có tài khoản nào sẵn sàng. Vui lòng liên hệ Admin cấu hình phiên trong Cài đặt."
              : "Threads collection needs setup. Ask an administrator to configure an account session in Settings."}
          </p>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" asChild className="gap-1.5">
              <Link href="/settings/account">
                <Settings size={13} />
                {language === "vi" ? "Đi đến Cài đặt" : "Open Settings"}
              </Link>
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setShowImportModal(true)}
              className="gap-1.5 text-xs text-slate-500 hover:text-slate-700"
            >
              <KeyRound size={13} />
              Import Session JSON (Admin)
            </Button>
          </div>
        </div>
      )}

      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}

      <Button
        type="submit"
        className={styles.startButton}
        disabled={busy || !ready || (!isDiscoveryPlanning && selectedCount === 0)}
      >
        <Play size={15} />
        {busy
          ? t("threads.starting")
          : isQueuing
            ? (language === "vi"
              ? `Thêm vào hàng đợi (${selectedCount} từ khóa)`
              : `Add to queue (${selectedCount} keywords)`)
            : isDiscoveryPlanning && selectedCount === 0
              ? (language === "vi"
                ? "Bắt đầu Discovery (Tự động lập kế hoạch)"
                : "Start Discovery (Auto-planning)")
              : (language === "vi"
                ? `Bắt đầu thu thập (${selectedCount} từ khóa đã chọn)`
                : `Start collection (${selectedCount} keywords)`)}
      </Button>
      {isQueuing && (
        <p className={styles.queueHint} role="status">
          <Clock3 size={14} />
          <span>
            {language === "vi"
              ? "Đang có phiên khác đang chạy. Phiên mới sẽ được lưu vào danh sách chờ và tự động bắt đầu ngay sau khi phiên trước chạy xong."
              : "Another collection is currently running. This session will be queued and will automatically run once the previous one finishes."}
          </span>
        </p>
      )}
      <p className={styles.formFootnote}>
        Duplicate posts within this collection are merged by ID or URL.
      </p>

      <ImportSessionModal
        open={showImportModal}
        onOpenChange={setShowImportModal}
        onSuccess={onRefreshConfig}
      />
    </form>
  );
}
