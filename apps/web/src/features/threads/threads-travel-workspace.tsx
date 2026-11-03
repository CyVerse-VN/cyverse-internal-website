"use client";

import { useState, useRef, useEffect } from "react";
import {
  Compass,
  MapPin,
  Sparkles,
  Utensils,
  Coffee,
  Sunset,
  Moon,
  Camera,
  Tent,
  ExternalLink,
  MessageSquare,
  ThumbsUp,
  Layers,
  Play,
  Square,
  Plus,
  X,
  CheckCircle2,
  AlertCircle,
  Download,
  Flame,
  Check,
  ChevronDown,
  SlidersHorizontal,
  LoaderCircle,
  FolderPlus,
  Trash2,
} from "lucide-react";

import { useLanguage } from "@/lib/i18n/context";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { threadsApi, ThreadsApiError } from "./api";
import {
  keywordAnalysisResponseSchema,
  threadsRunSchema,
  type ThreadsConfig,
  type ThreadsParameters,
  type ThreadsRun,
} from "./types";
import { isActiveRun } from "./settings";
import { ThreadsSessionControls } from "./threads-session-controls";
import { JsonExportControl } from "./json-export-control";
import { CrossSessionDedup } from "./cross-session-dedup";
import { ThreadsResults } from "./threads-results";
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

const STAGES = ["planning", "searching", "filtering", "comments", "curating", "saving"];
const STAGE_LABELS: Record<string, string> = {
  queued: "Waiting in queue",
  planning: "Planning the search",
  searching: "Collecting posts",
  filtering: "Filtering posts",
  comments: "Collecting comments",
  curating: "Analyzing results",
  saving: "Saving results",
  completed: "Collection complete",
  cancelled: "Collection cancelled",
  failed: "Collection failed",
};

interface ThreadsTravelWorkspaceProps {
  config: ThreadsConfig | null;
  history?: ThreadsRun[];
  selectedId?: string | null;
  activeRun?: ThreadsRun | null;
  cancelling?: boolean;
  onSelectRun?: (id: string | null) => void;
  onRunCreated?: (run: ThreadsRun) => void;
  onRunUpdated?: (run: ThreadsRun) => void;
  onCancelRun?: () => Promise<void>;
}

export function ThreadsTravelWorkspace({
  config,
  history = [],
  selectedId,
  activeRun: propActiveRun,
  cancelling = false,
  onSelectRun,
  onRunCreated,
  onRunUpdated,
  onCancelRun,
}: ThreadsTravelWorkspaceProps) {
  const { t, language } = useLanguage();

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

  // Scraper configuration identical to Threads Scraper tab
  const [parameters, setParameters] = useState<ThreadsParameters>({
    mode: "travel",
    keywords: [],
    max_posts_per_keyword: 50,
    search_type: "both", // Default to both recent and top for comprehensive local search
    check_duplicate: false,
    include_comments: true,
    max_comment_posts: -1,
    max_comments_per_post: 25,
    min_replies: 0,
    expand_query: false,
    keywords_per_query: 3,
    pre_filter: false,
    pre_filter_strictness: "none",
    curate: false,
    max_accounts: 3,
    use_proxy: true,
    run_timeout_seconds: -1, // Unlimited by default for continuous runner
    search_timeout_seconds: -1,
    min_delay_seconds: 2,
    max_delay_seconds: 4,
    discovery_mode: "legacy",
    query_planning: true,
    triage_provider: "groq",
    discovery_comment_posts: 20,
    use_manual_keywords: true,
  });
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Run execution state (standalone fallback or synced with props)
  const [localActiveRun, setLocalActiveRun] = useState<ThreadsRun | null>(null);
  const activeRun = propActiveRun ?? localActiveRun;
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"places" | "curated" | "poi">("places");
  const pollingRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (activeRun?.result?.discovery?.poi_candidates && activeRun.result.discovery.poi_candidates.length > 0) {
      setViewMode("poi");
    }
  }, [activeRun?.id, activeRun?.status, activeRun?.result?.discovery?.poi_candidates?.length]);

  function getStageLabel(stage: string): string {
    const stageMap = t("threads.stages") as unknown as Record<string, string>;
    return stageMap?.[stage] ?? STAGE_LABELS[stage] ?? stage;
  }

  // Analyze Keywords from Prompt via AI API, returning grouped categories
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

  // Keyword toggle and selection inside groups
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

  function updateParameters(patch: Partial<ThreadsParameters>) {
    setParameters((prev) => ({ ...prev, ...patch }));
  }

  // Start scraper session as normal
  async function handleStartCrawler() {
    if (!prompt.trim()) return;
    const isDiscoveryPlanning = parameters.discovery_mode === "evidence_poi" && parameters.query_planning;
    const activeKws = Array.from(selectedKeywords);
    if (!isDiscoveryPlanning && activeKws.length === 0) {
      setSubmitError(t("threads.noKeywordsSelected"));
      return;
    }

    setIsSubmitting(true);
    setSubmitError(null);

    const payload = {
      ...parameters,
      query: prompt.trim(),
      keywords: activeKws,
      visibility: "public" as const,
    };

    try {
      const run = await threadsApi("/runs", threadsRunSchema, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Idempotency-Key": crypto.randomUUID(),
        },
        body: JSON.stringify(payload),
      });

      if (onRunCreated) {
        onRunCreated(run);
      } else {
        setLocalActiveRun(run);
      }
    } catch (err) {
      setSubmitError(
        err instanceof ThreadsApiError
          ? err.message
          : err instanceof Error
          ? err.message
          : "Không thể khởi động phiên cào dữ liệu. Vui lòng thử lại."
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  // Standalone polling fallback if activeRun is not managed by parent
  useEffect(() => {
    if (!localActiveRun || propActiveRun) return;
    if (
      localActiveRun.status === "completed" ||
      localActiveRun.status === "failed" ||
      localActiveRun.status === "cancelled"
    ) {
      return;
    }

    const runId = localActiveRun.id;
    pollingRef.current = setTimeout(async () => {
      try {
        const item = await threadsApi(`/runs/${runId}`, threadsRunSchema);
        setLocalActiveRun(item);
      } catch {
        // Continue next tick
      }
    }, 2500);

    return () => {
      if (pollingRef.current) clearTimeout(pollingRef.current);
    };
  }, [localActiveRun, propActiveRun]);

  const isRunning = activeRun ? isActiveRun(activeRun.status) : false;
  const duplicateCount = activeRun?.result?.duplicate_count ?? 0;
  const postCount = activeRun?.post_count ?? activeRun?.result?.posts.length ?? 0;
  const commentCount = activeRun?.comment_count ?? activeRun?.result?.total_comments ?? 0;
  const posts = activeRun?.result?.posts ?? [];
  const selectedCount = selectedKeywords.size;
  const isDiscoveryPlanning = parameters.discovery_mode === "evidence_poi" && parameters.query_planning;

  const isUnlimitedComments = parameters.max_comments_per_post <= 0;
  const activeFilterLevel =
    !parameters.pre_filter || parameters.pre_filter_strictness === "none"
      ? "none"
      : parameters.pre_filter_strictness === "medium"
      ? "medium"
      : "high";

  return (
    <div className={styles.travelWorkspace}>
      {/* Top Banner: Context & Features */}
      <section className={styles.continuousHero}>
        <div className={styles.heroBadgesRow}>
          <div className={styles.badgePillDual}>
            <Flame size={14} />
            <span>{t("threads.dualModeBadge")}</span>
          </div>
          <div className={styles.badgePillLive}>
            <Layers size={14} />
            <span>{t("threads.continuousBadge")}</span>
          </div>
        </div>

      </section>

      {/* Main Configuration & Workflow Card (shown when no run is being reviewed or creating new) */}
      <div className={styles.crawlerCard}>
        {/* Step 1: Quick City Selector */}
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

        {/* Step 2: Topic / Prompt Input */}
        <div className={styles.travelSection}>
          <div className={styles.travelSectionHeader}>
            <label htmlFor="travel-prompt-input" className={styles.travelSectionLabel}>
              <Sparkles size={14} />
              {t("threads.travelPromptLabel")}
            </label>
            <span className={styles.promptLengthHint}>
              {prompt.length} / 1000 ký tự
            </span>
          </div>

          <div className={styles.promptAreaWrapper}>
            <textarea
              id="travel-prompt-input"
              className={styles.travelTextarea}
              rows={3}
              placeholder={t("threads.travelPromptPlaceholder")}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              disabled={isRunning || isSubmitting}
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
                disabled={isAnalyzing || !prompt.trim() || isRunning}
              >
                <Sparkles size={14} className={isAnalyzing ? styles.rotateIcon : ""} />
                {isAnalyzing ? t("threads.analyzingKeywords") : t("threads.analyzeKeywordsBtn")}
              </Button>
            </div>
          </div>

          {analysisError && (
            <div className={styles.analysisError} role="alert">
              <AlertCircle size={14} />
              <span>{analysisError}</span>
            </div>
          )}
        </div>

        {/* Step 3: Grouped Keywords Selection (Phân tích theo nhóm để tối ưu) */}
        <div className={styles.groupedKeywordsSection}>
          <div className={styles.groupedKeywordsHeader}>
            <div>
              <span className={styles.travelSectionLabel}>
                <Compass size={14} />
                {t("threads.groupedKeywordsTitle")} ({groups.length} nhóm chủ đề)
              </span>
              <p className={styles.keywordsDescHint}>
                {t("threads.groupedKeywordsDesc")}
              </p>
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

          {/* Inline Add New Group */}
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

          {/* Grouped Keyword Cards Grid */}
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

                  {/* Keywords in this group */}
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

                  {/* Inline Add Keyword into this Group */}
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

          {/* Selected Summary Bar */}
          <div className={styles.selectedSummaryRow}>
            <span>
              {t("threads.selectedKeywordsSummary")}:{" "}
              <strong className={styles.selectedCountHighlight}>
                {selectedCount} từ khóa
              </strong>{" "}
              (trên {groups.reduce((acc, g) => acc + g.keywords.length, 0)} từ khóa khả dụng)
            </span>
          </div>
          <CrossSessionDedup enabled={parameters.check_duplicate}
            onChange={(check_duplicate) => updateParameters({ check_duplicate })} />
        </div>

        {/* Step 4: Full Scraper Configuration identical to Threads Scraper tab */}
        <div className={styles.travelConfigCard}>
          <div className={styles.travelConfigHeader}>
            <h3>
              <SlidersHorizontal size={16} />
              <span>{t("threads.configTitle")} (Chi tiết thu thập)</span>
            </h3>
            <Badge variant="outline">Đầy đủ thông số Crawler</Badge>
          </div>

          {/* Search Order & Posts per Keyword */}
          <div className={styles.segmentedGroup}>
            <span>{t("threads.searchOrder")}</span>
            <div className={styles.segmentedControl}>
              <button
                type="button"
                className={styles.segmentedButton}
                data-active={parameters.search_type === "recent"}
                onClick={() => updateParameters({ search_type: "recent" })}
              >
                {t("threads.recent")}
              </button>
              <button
                type="button"
                className={styles.segmentedButton}
                data-active={parameters.search_type === "top"}
                onClick={() => updateParameters({ search_type: "top" })}
              >
                {t("threads.top")}
              </button>
              <button
                type="button"
                className={styles.segmentedButton}
                data-active={parameters.search_type === "both"}
                onClick={() => updateParameters({ search_type: "both" })}
              >
                {t("threads.searchBoth")}
              </button>
            </div>
          </div>

          {/* Posts per Keyword */}
          <div className={styles.segmentedGroup}>
            <span>{t("threads.postsPerKeyword")}</span>
            <div className={styles.segmentedGrid}>
              {[25, 50, 75, 100].map((count) => (
                <button
                  key={count}
                  type="button"
                  className={styles.segmentedGridButton}
                  data-active={parameters.max_posts_per_keyword === count}
                  onClick={() => updateParameters({ max_posts_per_keyword: count })}
                >
                  {count}
                </button>
              ))}
            </div>
            <small className={styles.hint}>{t("threads.postsPerKeywordHint")}</small>
          </div>

          {/* Comment Collection */}
          <label className={styles.toggle}>
            <input
              type="checkbox"
              checked={parameters.include_comments}
              onChange={(e) => updateParameters({ include_comments: e.target.checked })}
            />
            <span>
              <strong>{t("threads.commentsLabel")}</strong>
              <small>{t("threads.commentsDesc")}</small>
            </span>
          </label>

          {parameters.include_comments && (
            <fieldset className={styles.commentSettings}>
              <div className={styles.segmentedGroup}>
                <span>{t("threads.commentsLimit")}</span>
                <div className={styles.segmentedGrid}>
                  {[25, 50, 100].map((count) => (
                    <button
                      key={count}
                      type="button"
                      className={styles.segmentedGridButton}
                      data-active={parameters.max_comments_per_post === count}
                      onClick={() => updateParameters({ max_comments_per_post: count })}
                    >
                      {count}
                    </button>
                  ))}
                  <button
                    type="button"
                    className={styles.segmentedGridButton}
                    data-active={isUnlimitedComments}
                    onClick={() => updateParameters({ max_comments_per_post: -1 })}
                    title={t("threads.commentsAll")}
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

          {/* AI Assistance Section */}
          <div className={styles.segmentedGroup}>
            <span>{t("threads.preFilterStrictness")}</span>
            <div className={styles.segmentedControl}>
              <button
                type="button"
                className={styles.segmentedButton}
                data-active={activeFilterLevel === "none"}
                onClick={() =>
                  updateParameters({ pre_filter: false, pre_filter_strictness: "none" })
                }
              >
                {t("threads.strictnessNone")}
              </button>
              <button
                type="button"
                className={styles.segmentedButton}
                disabled={!config?.ai_available}
                data-active={activeFilterLevel === "medium"}
                onClick={() =>
                  updateParameters({ pre_filter: true, pre_filter_strictness: "medium" })
                }
              >
                {t("threads.strictnessMedium")}
              </button>
              <button
                type="button"
                className={styles.segmentedButton}
                disabled={!config?.ai_available}
                data-active={activeFilterLevel === "high"}
                onClick={() =>
                  updateParameters({ pre_filter: true, pre_filter_strictness: "high" })
                }
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

          {/* Discovery Engine V2 Options */}
          <div className={styles.segmentedGroup}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontWeight: 700, display: "flex", alignItems: "center", gap: 6 }}>
                <Compass size={14} />
                Chế độ Discovery Engine V2
              </span>
              <Badge variant={parameters.discovery_mode === "evidence_poi" ? "default" : "outline"}>
                {parameters.discovery_mode === "evidence_poi" ? "Active" : "Legacy"}
              </Badge>
            </div>
            <div className={styles.segmentedControl}>
              <button
                type="button"
                className={styles.segmentedButton}
                data-active={parameters.discovery_mode === "legacy"}
                onClick={() => updateParameters({ discovery_mode: "legacy" })}
              >
                Legacy Scraper
              </button>
              <button
                type="button"
                className={styles.segmentedButton}
                data-active={parameters.discovery_mode === "evidence_poi"}
                onClick={() => updateParameters({ discovery_mode: "evidence_poi" })}
              >
                POI Discovery Engine
              </button>
            </div>
            <small className={styles.hint}>
              {parameters.discovery_mode === "evidence_poi"
                ? "Khám phá địa điểm từ thảo luận, phân loại AI Triage, trích xuất POI có bằng chứng và entity resolution."
                : "Chế độ cào bài viết truyền thống theo từ khóa và bộ lọc sơ bộ."}
            </small>

            {parameters.discovery_mode === "evidence_poi" && (
              <div style={{ display: "grid", gap: 10, padding: 10, background: "rgb(125 140 160 / 6%)", borderRadius: 8, marginTop: 4 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: 12, fontWeight: 600 }}>Query Planning (Đa góc nhìn):</span>
                  <div className={styles.segmentedControl} style={{ maxWidth: 160 }}>
                    <button
                      type="button"
                      className={styles.segmentedButton}
                      data-active={parameters.query_planning}
                      onClick={() => updateParameters({ query_planning: true })}
                    >
                      Bật
                    </button>
                    <button
                      type="button"
                      className={styles.segmentedButton}
                      data-active={!parameters.query_planning}
                      onClick={() => updateParameters({ query_planning: false })}
                    >
                      Tắt
                    </button>
                  </div>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: 12, fontWeight: 600 }}>AI Triage Provider:</span>
                  <div className={styles.segmentedControl} style={{ maxWidth: 160 }}>
                    <button
                      type="button"
                      className={styles.segmentedButton}
                      data-active={parameters.triage_provider === "groq"}
                      onClick={() => updateParameters({ triage_provider: "groq" })}
                    >
                      Groq (Baseline)
                    </button>
                    {config?.triage_providers?.includes("jev") && (
                      <button
                        type="button"
                        className={styles.segmentedButton}
                        data-active={parameters.triage_provider === "jev"}
                        onClick={() => updateParameters({ triage_provider: "jev" })}
                      >
                        Jev AI
                      </button>
                    )}
                  </div>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: 12, fontWeight: 600 }}>Ngân sách cào bình luận:</span>
                  <div className={styles.segmentedControl} style={{ maxWidth: 200 }}>
                    {[10, 20, 30, 50].map((b) => (
                      <button
                        key={b}
                        type="button"
                        className={styles.segmentedButton}
                        data-active={parameters.discovery_comment_posts === b}
                        onClick={() => updateParameters({ discovery_comment_posts: b })}
                      >
                        {b} bài
                      </button>
                    ))}
                  </div>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: 12, fontWeight: 600 }}>Giữ keyword thủ công làm seed:</span>
                  <div className={styles.segmentedControl} style={{ maxWidth: 160 }}>
                    <button
                      type="button"
                      className={styles.segmentedButton}
                      data-active={parameters.use_manual_keywords}
                      onClick={() => updateParameters({ use_manual_keywords: true })}
                    >
                      Giữ seeds
                    </button>
                    <button
                      type="button"
                      className={styles.segmentedButton}
                      data-active={!parameters.use_manual_keywords}
                      onClick={() => updateParameters({ use_manual_keywords: false })}
                    >
                      Chỉ AI
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Advanced Settings Dropdown */}
          <div>
            <button
              type="button"
              className={styles.fineTuneToggle}
              onClick={() => setShowAdvanced((prev) => !prev)}
              aria-expanded={showAdvanced}
            >
              <div>
                <SlidersHorizontal size={14} />
                <span>
                  {showAdvanced
                    ? t("threads.hideAdvancedSettings")
                    : t("threads.advancedSettings")}
                </span>
              </div>
              <ChevronDown
                size={14}
                className={showAdvanced ? styles.rotate180 : undefined}
              />
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
                        onClick={() => updateParameters(val === -1 ? { run_timeout_seconds: -1, search_timeout_seconds: -1 } : { run_timeout_seconds: val })}
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
                        onClick={() =>
                          updateParameters({ search_timeout_seconds: val })
                        }
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                  <small className={styles.hint}>
                    {t("threads.searchTimeoutHint")}
                  </small>
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
                            onClick={() =>
                              updateParameters({ max_comment_posts: val })
                            }
                          >
                            {label}
                          </button>
                        ))}
                      </div>
                      <small className={styles.hint}>
                        {t("threads.maxCommentPostsHint")}
                      </small>
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
                            onClick={() => updateParameters({ min_replies: val })}
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
                      data-active={
                        parameters.min_delay_seconds === 1 &&
                        parameters.max_delay_seconds === 2
                      }
                      onClick={() =>
                        updateParameters({
                          min_delay_seconds: 1,
                          max_delay_seconds: 2,
                        })
                      }
                    >
                      {t("threads.delaysFast")}
                    </button>
                    <button
                      type="button"
                      className={styles.segmentedButton}
                      data-active={
                        parameters.min_delay_seconds === 2 &&
                        parameters.max_delay_seconds === 4
                      }
                      onClick={() =>
                        updateParameters({
                          min_delay_seconds: 2,
                          max_delay_seconds: 4,
                        })
                      }
                    >
                      {t("threads.delaysNormal")}
                    </button>
                    <button
                      type="button"
                      className={styles.segmentedButton}
                      data-active={
                        parameters.min_delay_seconds === 4 &&
                        parameters.max_delay_seconds === 8
                      }
                      onClick={() =>
                        updateParameters({
                          min_delay_seconds: 4,
                          max_delay_seconds: 8,
                        })
                      }
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
                        onClick={() => updateParameters({ max_accounts: val })}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                  <small className={styles.hint}>{t("threads.maxAccountsHint")}</small>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Step 5: Start Button Bar */}
        <div className={styles.launchButtonBar}>
          <Button
            type="button"
            className={styles.startCrawlerBtn}
            onClick={handleStartCrawler}
            disabled={isSubmitting || (!isDiscoveryPlanning && selectedCount === 0)}
          >
            <Play size={16} />
            {isSubmitting
              ? "Đang chuẩn bị phiên..."
              : isDiscoveryPlanning && selectedCount === 0
              ? "Bắt đầu Discovery (Tự động lập kế hoạch từ Prompt)"
              : `Bắt đầu cào dữ liệu (${selectedCount} từ khóa đã chọn)`}
          </Button>

          {submitError && (
            <div className={styles.runErrorNotice} role="alert">
              <AlertCircle size={15} />
              <span>{submitError}</span>
            </div>
          )}
        </div>
      </div>

      {/* Step 6: Real-time Execution & Results ("sau đó hệ thống sẽ chạy như bình thường") */}
      {activeRun && (
        <section className={styles.liveStatsCard} aria-label="Chi tiết phiên cào dữ liệu">
          <div className={styles.statsCardHeader}>
            <div>
              <div className={styles.heroBadgesRow}>
                <Badge
                  variant={
                    activeRun.status === "failed"
                      ? "destructive"
                      : activeRun.status === "completed"
                      ? "success"
                      : "secondary"
                  }
                >
                  {activeRun.status.toUpperCase()}
                </Badge>
                {activeRun.request.check_duplicate && (
                  <span className={styles.verifiedDedupBadge}>
                    <CheckCircle2 size={12} />
                    Luôn lọc trùng lặp
                  </span>
                )}
                <span className={styles.dualModePill}>
                  {activeRun.request.search_type === "both"
                    ? "Top + Mới nhất"
                    : activeRun.request.search_type === "top"
                    ? "Top posts"
                    : "Mới nhất"}
                </span>
              </div>
              <h3 style={{ marginTop: 6 }}>{activeRun.request.query}</h3>
              <p>
                Mã phiên: {activeRun.id} • Khởi tạo:{" "}
                {new Date(activeRun.created_at).toLocaleString(
                  language === "vi" ? "vi-VN" : "en",
                  { dateStyle: "medium", timeStyle: "short" }
                )}
              </p>
            </div>

            <div className={styles.headingActions}>
              {onSelectRun && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onSelectRun(null)}
                >
                  <Plus size={14} />
                  Tạo phiên cào mới
                </Button>
              )}
            </div>
          </div>

          {/* Session Controls */}
          {onRunUpdated && (
            <ThreadsSessionControls
              key={activeRun.id}
              run={activeRun}
              onUpdated={onRunUpdated}
            />
          )}

          {/* Live Progress Bar when running */}
          {isRunning && (
            <div className={styles.progressPanel} role="status" aria-live="polite">
              <div>
                <LoaderCircle size={16} className={styles.spinner} />
                <strong>{getStageLabel(activeRun.stage)}</strong>
                <span>{Math.round(activeRun.progress * 100)}%</span>
              </div>
              <progress value={activeRun.progress} max={1} aria-label="Collection progress" />
              <p>{t("threads.backgroundNotice")}</p>
              {activeRun.can_manage && onCancelRun && (
                <Button
                  variant="outline"
                  size="sm"
                  disabled={cancelling || activeRun.deletion_requested}
                  onClick={onCancelRun}
                >
                  <Square size={14} />
                  {cancelling ? t("threads.cancelling") : "Dừng cào dữ liệu"}
                </Button>
              )}
            </div>
          )}

          {/* Metrics Grid including Deduplication Filtered Count */}
          <div className={styles.metricsGrid}>
            <div className={styles.metricBox}>
              <div className={styles.metricVal}>{postCount}</div>
              <div className={styles.metricLabel}>{t("threads.uniquePostsCount")}</div>
              <small className={styles.metricSub}>Đã lưu trữ độc lập</small>
            </div>

            <div className={`${styles.metricBox} ${styles.metricBoxDedup}`}>
              <div className={styles.metricVal}>{duplicateCount}</div>
              <div className={styles.metricLabel}>{t("threads.dedupFilteredCount")}</div>
              <small className={styles.metricSub}>Trùng ID/URL đã lọc bỏ</small>
            </div>

            <div className={styles.metricBox}>
              <div className={styles.metricVal}>{commentCount}</div>
              <div className={styles.metricLabel}>Bình luận thu thập</div>
              <small className={styles.metricSub}>Chứa review và mẹo quán</small>
            </div>

            <div className={styles.metricBox}>
              <div className={styles.metricVal}>
                {activeRun.result ? `${activeRun.result.duration_seconds}s` : "..."}
              </div>
              <div className={styles.metricLabel}>Thời gian thực thi</div>
              <small className={styles.metricSub}>Giai đoạn: {activeRun.stage}</small>
            </div>
          </div>

          {/* Stage list */}
          <ol className={styles.stageList} aria-label="Collection stages">
            {STAGES.map((stage, index) => {
              const done =
                activeRun.status === "completed" ||
                (isActiveRun(activeRun.status) && STAGES.indexOf(activeRun.stage) > index);
              return (
                <li key={stage} data-active={stage === activeRun.stage} data-done={done}>
                  {done ? <Check size={11} /> : <span>{index + 1}</span>}
                  {getStageLabel(stage)}
                </li>
              );
            })}
          </ol>

          {activeRun.status === "cancelled" && (
            <p className={styles.notice} style={{ margin: "16px 0" }}>
              Phiên cào đã được hủy. Quá trình thu thập đã dừng và toàn bộ dữ liệu đã được xóa sạch.
            </p>
          )}

          {/* Export links */}
          {activeRun.result && activeRun.result.posts.length > 0 && !isActiveRun(activeRun.status) && activeRun.status !== "cancelled" && (
            <div className={styles.exportBar}>
              <span>Xuất toàn bộ kết quả đã cào:</span>
              <div className={styles.exportButtons}>
                <JsonExportControl runId={activeRun.id} />
                <a
                  href={`/api/threads/runs/${activeRun.id}/export?format=txt`}
                  download
                  className={styles.exportActionBtn}
                >
                  <Download size={14} />
                  <span>Tải Báo cáo TXT</span>
                </a>
              </div>
            </div>
          )}

          {/* View mode toggle between Places Cards and Scraper Curation View */}
          {activeRun.result && activeRun.status !== "cancelled" && posts.length > 0 && (
            <div>
              <div className={styles.segmentedControl} style={{ maxWidth: 360, margin: "16px 0 12px" }}>
                <button
                  type="button"
                  className={styles.segmentedButton}
                  data-active={viewMode === "places"}
                  onClick={() => setViewMode("places")}
                >
                  Bản tin bài viết ({posts.length})
                </button>
                <button
                  type="button"
                  className={styles.segmentedButton}
                  data-active={viewMode === "curated"}
                  onClick={() => setViewMode("curated")}
                >
                  Bảng phân tích Scraper
                </button>
                {activeRun.result?.discovery?.poi_candidates && activeRun.result.discovery.poi_candidates.length > 0 && (
                  <button
                    type="button"
                    className={styles.segmentedButton}
                    data-active={viewMode === "poi"}
                    onClick={() => setViewMode("poi")}
                  >
                    Địa điểm phát hiện ({activeRun.result.discovery.poi_candidates.length})
                  </button>
                )}
              </div>

              {viewMode === "curated" ? (
                <ThreadsResults key={activeRun.id} run={activeRun} />
              ) : viewMode === "poi" ? (
                <div className={styles.placesList}>
                  {activeRun.result?.discovery?.poi_candidates?.map((cand, idx) => (
                    <article key={cand.id || idx} className={styles.placeCard} style={{ borderLeft: "4px solid var(--blue-600)" }}>
                      <div className={styles.placeCardHeader}>
                        <div className={styles.placeTitleGroup}>
                          <h4 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>{cand.canonical_name}</h4>
                          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 4 }}>
                            {cand.category && (
                              <Badge variant="outline">{cand.category}</Badge>
                            )}
                            {cand.area && (
                              <Badge variant="secondary"><MapPin size={11} style={{ marginRight: 3 }} />{cand.area}</Badge>
                            )}
                            <Badge variant={cand.verification_status === "verified" ? "default" : "secondary"}>
                              {cand.verification_status === "verified" ? "Đã xác minh qua nhiều nguồn" : "Ứng viên (Cần kiểm chứng)"}
                            </Badge>
                            <span style={{ fontSize: 11, color: "var(--muted)", alignSelf: "center" }}>
                              {cand.distinct_sources_count} nguồn độc lập
                            </span>
                          </div>
                        </div>
                      </div>

                      {cand.address && (
                        <p style={{ fontSize: 13, color: "var(--ink)", margin: "8px 0" }}>
                          📍 <strong>Địa chỉ trích xuất:</strong> {cand.address}
                        </p>
                      )}

                      {cand.claims && cand.claims.length > 0 && (
                        <div style={{ marginTop: 10, display: "grid", gap: 6 }}>
                          <strong style={{ fontSize: 12 }}>Đặc trưng & Đánh giá từ cộng đồng:</strong>
                          {cand.claims.map((claim, cIdx) => (
                            <div key={cIdx} style={{ fontSize: 12, background: "rgb(125 140 160 / 7%)", padding: "6px 10px", borderRadius: 6 }}>
                              <span style={{ fontWeight: 600, color: claim.claim_type === "warning" || claim.claim_type === "closure" ? "var(--red-600)" : "var(--blue-600)" }}>
                                [{claim.claim_type.toUpperCase()}]
                              </span>{" "}
                              <span>{claim.value}</span>
                              <div style={{ fontStyle: "italic", color: "var(--muted)", marginTop: 2 }}>
                                “{claim.evidence_text}”
                              </div>
                            </div>
                          ))}
                        </div>
                      )}

                      {cand.mentions && cand.mentions.length > 0 && (
                        <div style={{ marginTop: 12, borderTop: "1px dashed var(--line)", paddingTop: 8 }}>
                          <small style={{ color: "var(--muted)" }}>
                            Bằng chứng nguồn từ Threads:
                          </small>
                          {cand.mentions.slice(0, 3).map((m, mIdx) => (
                            <div key={mIdx} style={{ fontSize: 11, color: "var(--muted)", marginTop: 2 }}>
                              • Post {m.source_post_id}: “{m.evidence_text}”
                            </div>
                          ))}
                        </div>
                      )}
                    </article>
                  ))}
                </div>
              ) : (
                <div className={styles.placesList}>
                  {posts.map((post) => (
                    <article key={post.post_id} className={styles.placeCard}>
                      <div className={styles.placeCardHeader}>
                        <div className={styles.placeTitleGroup}>
                          <div className={styles.postAuthorBadge}>
                            <strong>@{post.username}</strong>
                            <span className={styles.verifiedDedupBadge}>
                              <CheckCircle2 size={12} />
                              Đã lọc trùng lặp
                            </span>
                            <span className={styles.dualModePill}>
                              {activeRun.request.search_type === "both"
                                ? "Top & Gần đây"
                                : activeRun.request.search_type}
                            </span>
                          </div>
                          {post.published_at && (
                            <span className={styles.postDate}>{post.published_at}</span>
                          )}
                        </div>
                        <div className={styles.postEngagement}>
                          <span className={styles.metaItem}>
                            <ThumbsUp size={13} />
                            {post.like_count}
                          </span>
                          <span className={styles.metaItem}>
                            <MessageSquare size={13} />
                            {post.reply_count}
                          </span>
                        </div>
                      </div>

                      <p className={styles.postBodyText}>{post.text}</p>

                      {post.search_keywords && post.search_keywords.length > 0 && (
                        <div className={styles.matchedKeywordsRow}>
                          <span className={styles.kwMatchLabel}>Keywords khớp:</span>
                          {post.search_keywords.map((k) => (
                            <span key={k} className={styles.placeTag}>
                              #{k}
                            </span>
                          ))}
                        </div>
                      )}

                      {post.comments && post.comments.length > 0 && (
                        <div className={styles.threadsCommentBox}>
                          <div className={styles.threadsCommentHeader}>
                            <MessageSquare size={13} />
                            <span>Bình luận cộng đồng:</span>
                          </div>
                          <blockquote>“{post.comments[0].text}”</blockquote>
                        </div>
                      )}

                      <div className={styles.placeFooter}>
                        <span className={styles.postIdHint}>Post ID: {post.post_id}</span>
                        <a
                          href={post.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className={styles.viewThreadsBtn}
                        >
                          <span>Xem bài viết gốc trên Threads</span>
                          <ExternalLink size={13} />
                        </a>
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </div>
          )}
        </section>
      )}

      {/* When no run has been executed yet, show empty prompt state */}
      {!activeRun && (
        <section className={styles.emptyPromptState}>
          <Compass size={36} />
          <h4>Sẵn sàng cào dữ liệu địa điểm du lịch &amp; quán ngon</h4>
          <p>
            Nhập prompt mong muốn ở trên, nhấn <strong>Phân tích Keyword (AI)</strong> để AI nhóm các từ khóa tối ưu. Sau đó bạn có thể tùy chỉnh các cấu hình tương tự như tab Threads Scraper và bấm <strong>Bắt đầu cào dữ liệu</strong>.
          </p>

          {history.length > 0 && onSelectRun && (
            <div style={{ marginTop: 20, width: "100%", maxWidth: 600 }}>
              <p style={{ fontSize: 12, fontWeight: 700, color: "var(--ink)", marginBottom: 8 }}>
                Hoặc xem lại kết quả các phiên thu thập gần đây:
              </p>
              <div className={styles.chipsRow} style={{ justifyContent: "center" }}>
                {history.slice(0, 6).map((h) => (
                  <button
                    key={h.id}
                    type="button"
                    className={styles.chipButton}
                    data-active={h.id === selectedId}
                    onClick={() => onSelectRun(h.id)}
                  >
                    {h.request.query} ({h.post_count} bài)
                  </button>
                ))}
              </div>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
