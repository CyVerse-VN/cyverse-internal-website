export type Language = "en" | "vi";

export interface TranslationDictionary {
  nav: {
    home: string;
    research: string;
    threads: string;
    datasets: string;
    experiments: string;
    monitoring: string;
    documents: string;
    users: string;
    soon: string;
    collapse: string;
    expand: string;
  };
  auth: {
    welcomeBack: string;
    subtitle: string;
    username: string;
    password: string;
    usernamePlaceholder: string;
    passwordPlaceholder: string;
    usernameHint: string;
    show: string;
    hide: string;
    signIn: string;
    signingIn: string;
    needAccount: string;
  };
  topbar: {
    platform: string;
    tools: string;
    admin: string;
    account: string;
    searchPlaceholder: string;
    toggleTheme: string;
    toggleLanguage: string;
    lightMode: string;
    darkMode: string;
  };
  account: {
    settings: string;
    profileSecurity: string;
    userManagement: string;
    manageAccounts: string;
    signOut: string;
    endSession: string;
    signingOut: string;
    adminRole: string;
    memberRole: string;
  };
  dashboard: {
    greeting: string;
    subtitle: string;
    overview: string;
    availableTools: string;
    launchTool: string;
    recentActivity: string;
    deepfakeTitle: string;
    deepfakeDesc: string;
    videoTitle: string;
    videoDesc: string;
    explainTitle: string;
    explainDesc: string;
    datasetTitle: string;
    datasetDesc: string;
    activeRuns: string;
    systemStatus: string;
    connectedAPIs: string;
    demoPill: string;
    tagline: string;
    quote: string;
    quoteAuthor: string;
    availableToolsMetric: string;
    datasetsMetric: string;
    experimentsMetric: string;
    teamMembersMetric: string;
    popularTools: string;
    popularToolsSubtitle: string;
    comingSoon: string;
    noToolsFound: string;
    noToolsDesc: string;
    sampleActivity: string;
    activityItemTitle: string;
    activityItemMeta: string;
    completed: string;
    adminRequiredNotice: string;
  };
  settings: {
    eyebrow: string;
    heading: string;
    subheading: string;
    role: string;
    team: string;
    status: string;
    active: string;
    inactive: string;
    notAssigned: string;
    profileHeading: string;
    profileSubheading: string;
    username: string;
    usernameHint: string;
    displayName: string;
    displayNameHint: string;
    displayNamePlaceholder: string;
    teamHint: string;
    teamPlaceholder: string;
    notebooklmEmail: string;
    notebooklmHint: string;
    saveProfile: string;
    saving: string;
    securityHeading: string;
    securitySubheading: string;
    currentPassword: string;
    currentPasswordPlaceholder: string;
    newPassword: string;
    newPasswordPlaceholder: string;
    confirmPassword: string;
    confirmPasswordPlaceholder: string;
    passwordHint: string;
    updatePassword: string;
    updating: string;
  };
  threads: {
    tabScraper: string;
    tabTravel: string;
    travelHeading: string;
    travelSubheading: string;
    travelEyebrow: string;
    travelCityLabel: string;
    travelCategoryLabel: string;
    travelQueryPlaceholder: string;
    travelPreviewBadge: string;
    travelPreviewNotice: string;
    searchBoth: string;
    travelPromptLabel: string;
    travelPromptPlaceholder: string;
    analyzeKeywordsBtn: string;
    analyzingKeywords: string;
    analyzedKeywordsTitle: string;
    analyzedKeywordsHint: string;
    addKeywordPlaceholder: string;
    dualModeTitle: string;
    dualModeBadge: string;
    dedupBadge: string;
    dedupNotice: string;
    continuousTitle: string;
    continuousBadge: string;
    startCrawlerBtn: string;
    dedupFilteredCount: string;
    uniquePostsCount: string;
    groupedKeywordsTitle: string;
    groupedKeywordsDesc: string;
    selectAllInGroup: string;
    deselectAllInGroup: string;
    addKeywordToGroup: string;
    addKeywordGroup: string;
    newGroupName: string;
    selectedKeywordsSummary: string;
    noKeywordsSelected: string;
    removeGroup: string;
    heading: string;
    subheading: string;
    configTitle: string;
    reset: string;
    queryLabel: string;
    queryPlaceholder: string;
    queryHint: string;
    keywordsLabel: string;
    keywordsPlaceholder: string;
    keywordsHint: string;
    optional: string;
    postsPerKeyword: string;
    searchOrder: string;
    recent: string;
    top: string;
    commentsLabel: string;
    commentsDesc: string;
    postsWithComments: string;
    commentsPerPost: string;
    minReplies: string;
    presetsTitle: string;
    presetBalanced: string;
    presetBalancedDesc: string;
    presetDeep: string;
    presetDeepDesc: string;
    presetFast: string;
    presetFastDesc: string;
    commentsLimit: string;
    commentsAll: string;
    commentsAllNotice: string;
    postsWithCommentsOption: string;
    postsWithCommentsAll: string;
    preFilterStrictness: string;
    strictnessNone: string;
    strictnessNoneDesc: string;
    strictnessMedium: string;
    strictnessMediumDesc: string;
    strictnessHigh: string;
    strictnessHighDesc: string;
    advancedSettings: string;
    hideAdvancedSettings: string;
    maxAccountsLabel: string;
    maxAccountsAll: string;
    maxAccountsHint: string;
    accountUnit: string;
    accountsUnit: string;
    useProxyLabel: string;
    useProxyHint: string;
    runTimeoutLabel: string;
    runTimeoutHint: string;
    runTimeoutUnlimited: string;
    runTimeoutUnlimitedNotice: string;
    searchTimeoutLabel: string;
    searchTimeoutHint: string;
    delaysLabel: string;
    delaysHint: string;
    delaysFast: string;
    delaysNormal: string;
    delaysSafe: string;
    minRepliesHint: string;
    maxCommentPostsHint: string;
    postsPerKeywordHint: string;
    commentsUnlimited: string;
    aiTitle: string;
    aiUnavailable: string;
    expandQuery: string;
    expandQueryDesc: string;
    keywordsCountLabel: string;
    keywordsCountHint: string;
    preFilter: string;
    preFilterDesc: string;
    curate: string;
    curateDesc: string;
    startCollection: string;
    starting: string;
    cancel: string;
    welcomeTitle: string;
    welcomeDesc: string;
    historyTitle: string;
    emptyHistory: string;
    exportJSON: string;
    eyebrow: string;
    configured: string;
    setupRequired: string;
    newCollection: string;
    fromConversationToContext: string;
    welcomeHeading: string;
    welcomeSubtitle: string;
    step1: string;
    step2: string;
    step3: string;
    reuseSettings: string;
    collectionProgress: string;
    backgroundNotice: string;
    cancelCollection: string;
    cancelling: string;
    cancelledNotice: string;
    failedNotice: string;
    collectionResults: string;
    exportJson: string;
    exportTxt: string;
    postsCollected: string;
    comments: string;
    curatedPosts: string;
    collectionTime: string;
    filterSearchPlaceholder: string;
    curatedOnly: string;
    postsShown: string;
    noPostsTitle: string;
    noPostsFiltered: string;
    noPostsEmpty: string;
    likes: string;
    replies: string;
    reposts: string;
    mediaItems: string;
    relevant: string;
    lowerRelevance: string;
    collectedComments: string;
    replyingTo: string;
    openPost: string;
    noCaption: string;
    historyHeading: string;
    activeSearches: string;
    savedSearches: string;
    loadingHistory: string;
    emptyHistoryHint: string;
    loadMoreCollections: string;
    loading: string;
    stages: Record<string, string>;
  };
  research: {
    heading: string;
    subheading: string;
    searchPlaceholder: string;
    searchButton: string;
    searching: string;
    advancedSettings: string;
    hideAdvancedSettings: string;
    paperLimits: string;
    timeRange: string;
    allTime: string;
    from2025: string;
    from2024: string;
    from2023: string;
    customRange: string;
    historyTitle: string;
    newSession: string;
    emptyHistory: string;
    downloadPDF: string;
    openPDF: string;
    renameSession: string;
    deleteSession: string;
    breadcrumb: string;
    quote: string;
    searchCardTitle: string;
    searchCardDesc: string;
    sourcesLegend: string;
    maxResults: string;
    papersCount: string;
    visibility: string;
    public: string;
    private: string;
    customYearsTitle: string;
    customYearsDesc: string;
    yearFrom: string;
    yearTo: string;
    minYear: string;
    maxYear: string;
    candidateExtractionLimits: string;
    candidateExtractionDesc: string;
    resetDefaults: string;
    loadOlder: string;
    startSession: string;
    startSessionDesc: string;
    loadingSession: string;
    searchResults: string;
    papersShown: string;
    sortBy: string;
    relevance: string;
    newest: string;
    citations: string;
    title: string;
    filters: string;
    clear: string;
    pubYear: string;
    allYears: string;
    source: string;
    allSources: string;
    paperType: string;
    allTypes: string;
    topic: string;
    allTopics: string;
    priority: string;
    allPriorities: string;
    high: string;
    medium: string;
    low: string;
    openAccessOnly: string;
    noPapersMatch: string;
    clearFilters: string;
    open: string;
    unavailable: string;
    openAccessBadge: string;
    citationsCount: string;
    aiSummary: string;
    abstractBasis: string;
    whyReadThis: string;
    deleteTitle: string;
    deleteConfirm: string;
    deleteButton: string;
    cancelButton: string;
  };
  admin: {
    heading: string;
    subheading: string;
    searchPlaceholder: string;
    newUser: string;
    editUser: string;
    createUser: string;
    username: string;
    displayName: string;
    role: string;
    team: string;
    status: string;
    actions: string;
    deactivate: string;
    activate: string;
    edit: string;
    closeDialog: string;
    eyebrow: string;
    createEyebrow: string;
    createTitle: string;
    createDesc: string;
    editEyebrow: string;
    editTitle: string;
    editDesc: string;
    passwordEyebrow: string;
    passwordTitle: string;
    passwordDesc: string;
    required: string;
    optional: string;
    usernameHint: string;
    displayNameHint: string;
    teamHint: string;
    member: string;
    administrator: string;
    roleHint: string;
    tempPassword: string;
    tempPasswordHint: string;
    notebooklmEmail: string;
    notebooklmHint: string;
    cancel: string;
    creating: string;
    saveChanges: string;
    saving: string;
    updatePassword: string;
    updating: string;
    newTempPassword: string;
    newTempPasswordHint: string;
    password: string;
    selfRoleHint: string;
    search: string;
    searching: string;
    created: string;
    emptyTitle: string;
    emptyDesc: string;
    usersCount: string;
    userCount: string;
    previous: string;
    next: string;
    pageOf: string;
    confirmDeactivate: string;
    confirmActivate: string;
    active: string;
    inactive: string;
  };
}

export const translations: Record<Language, TranslationDictionary> = {
  en: {
    nav: {
      home: "Home",
      research: "AI Research Tool",
      threads: "Threads Scraper",
      datasets: "Datasets",
      experiments: "Experiments",
      monitoring: "Monitoring",
      documents: "Documents",
      users: "User Management",
      soon: "Soon",
      collapse: "Collapse navigation",
      expand: "Expand navigation",
    },
    auth: {
      welcomeBack: "Welcome back",
      subtitle: "Sign in to CyVerse internal platform",
      username: "Username",
      password: "Password",
      usernamePlaceholder: "Username",
      passwordPlaceholder: "Password",
      usernameHint: "Letters, numbers, dots, hyphens, or underscores.",
      show: "Show",
      hide: "Hide",
      signIn: "Sign in",
      signingIn: "Signing in…",
      needAccount: "Need an account? Contact your administrator.",
    },
    topbar: {
      platform: "Platform",
      tools: "Tools",
      admin: "Administration",
      account: "Account",
      searchPlaceholder: "Search anything in CyVerse...",
      toggleTheme: "Toggle theme",
      toggleLanguage: "Switch language",
      lightMode: "Light mode",
      darkMode: "Dark mode",
    },
    account: {
      settings: "Account settings",
      profileSecurity: "Profile & security",
      userManagement: "User Management",
      manageAccounts: "Manage accounts & roles",
      signOut: "Sign out",
      endSession: "End this session",
      signingOut: "Signing out…",
      adminRole: "Administrator",
      memberRole: "Member",
    },
    dashboard: {
      greeting: "Hello",
      subtitle: "Secure internal tools for explainable AI and trusted media workflows.",
      overview: "Platform Overview",
      availableTools: "Available Tools",
      launchTool: "Launch Tool",
      recentActivity: "Recent Activity",
      deepfakeTitle: "Deepfake Detection",
      deepfakeDesc: "Detect manipulated images and videos with explainable AI.",
      videoTitle: "Video Analysis",
      videoDesc: "Analyze video and extract key frames and metadata.",
      explainTitle: "Explainability Viewer",
      explainDesc: "Visualize model explanations and attention maps.",
      datasetTitle: "Dataset Manager",
      datasetDesc: "Manage, preview, and label training datasets.",
      activeRuns: "Active Runs",
      systemStatus: "System Status",
      connectedAPIs: "Connected APIs",
      demoPill: "Demo data",
      tagline: "Build, experiment, and deploy explainable deepfake detection — together.",
      quote: "“More trustworthy media for a safer tomorrow.”",
      quoteAuthor: "— CyVerse",
      availableToolsMetric: "Available Tools",
      datasetsMetric: "Datasets",
      experimentsMetric: "Experiments",
      teamMembersMetric: "Team Members",
      popularTools: "Popular Tools",
      popularToolsSubtitle: "Curated for your team",
      comingSoon: "Coming soon",
      noToolsFound: "No tools found",
      noToolsDesc: "Try a different search term.",
      sampleActivity: "Sample activity",
      activityItemTitle: "Deepfake Detection analysis completed",
      activityItemMeta: "Sample video · 2 hours ago",
      completed: "Completed",
      adminRequiredNotice: "Administrator access is required for User Management.",
    },
    settings: {
      eyebrow: "Personal workspace",
      heading: "Account Settings",
      subheading: "Manage your personal details and keep your account secure.",
      role: "Role",
      team: "Team",
      status: "Status",
      active: "Active",
      inactive: "Inactive",
      notAssigned: "Not assigned",
      profileHeading: "Profile details",
      profileSubheading: "This information appears across your workspace.",
      username: "Username",
      usernameHint: "Usernames are permanent and managed by an administrator.",
      displayName: "Display name",
      displayNameHint: "Use the name teammates will recognize.",
      displayNamePlaceholder: "e.g. CyVerse",
      teamHint: "Optional. Helps teammates understand where you work.",
      teamPlaceholder: "e.g. Data Platform",
      notebooklmEmail: "Preferred NotebookLM email",
      notebooklmHint: "Connect this Google account in the extension before importing papers. You can change it any time.",
      saveProfile: "Save profile",
      saving: "Saving…",
      securityHeading: "Password & security",
      securitySubheading: "Changing your password signs out every other session.",
      currentPassword: "Current password",
      currentPasswordPlaceholder: "Enter your current password",
      newPassword: "New password",
      newPasswordPlaceholder: "At least 8 characters",
      confirmPassword: "Confirm password",
      confirmPasswordPlaceholder: "Repeat the new password",
      passwordHint: "Use 8–128 characters and avoid reusing your current password.",
      updatePassword: "Update password",
      updating: "Updating…",
    },
    threads: {
      tabScraper: "Threads Scraper",
      tabTravel: "Travel & Places",
      travelHeading: "Travel & Places Discovery",
      travelSubheading: "Specialized tool to discover hidden gems, quiet cafes, and local spots around cities from authentic Threads conversations.",
      travelEyebrow: "TRAVEL & LOCAL SPOTS INTELLIGENCE",
      travelCityLabel: "Popular destinations",
      travelCategoryLabel: "Category of interest",
      travelQueryPlaceholder: "e.g. Hidden local food spots and quiet cafes around Ho Chi Minh City...",
      travelPreviewBadge: "Specialized Mode",
      travelPreviewNotice: "Travel Mode UI Preview — Dedicated extraction for hidden gems, locations, and authentic reviews from locals.",
      searchBoth: "Both (Recent & Top)",
      travelPromptLabel: "Topic or Place Prompt",
      travelPromptPlaceholder: "Describe what you want to crawl (e.g. Find hidden gem street food, local eateries, chill sunset cafes around Saigon...)",
      analyzeKeywordsBtn: "Analyze Keywords (AI)",
      analyzingKeywords: "Analyzing...",
      analyzedKeywordsTitle: "Auto-Analyzed Keywords",
      analyzedKeywordsHint: "The crawler will search BOTH modes (Recent + Top) for every keyword below.",
      addKeywordPlaceholder: "Add custom keyword...",
      dualModeTitle: "Search Mode",
      dualModeBadge: "Dual Mode: Recent & Top Posts (Locked)",
      dedupBadge: "Always Deduplicate (Active)",
      dedupNotice: "Automatically checks post IDs and history to eliminate all duplicates across keywords and between Recent and Top searches.",
      continuousTitle: "Continuous Crawler (Treo tool)",
      continuousBadge: "Continuous Runner Ready",
      startCrawlerBtn: "Start Continuous Crawler",
      dedupFilteredCount: "Duplicates Filtered",
      uniquePostsCount: "Unique Posts",
      groupedKeywordsTitle: "AI Grouped Keywords",
      groupedKeywordsDesc: "AI has categorized keywords into thematic groups to optimize search coverage.",
      selectAllInGroup: "Select all",
      deselectAllInGroup: "Deselect all",
      addKeywordToGroup: "Add keyword to group",
      addKeywordGroup: "Add topic group",
      newGroupName: "New group name...",
      selectedKeywordsSummary: "Keywords selected for collection",
      noKeywordsSelected: "No keywords selected. Please select at least one keyword.",
      removeGroup: "Remove group",
      heading: "Threads Scraper",
      subheading: "Collect, analyze, and export public threads with AI-assisted research tools.",
      configTitle: "Configure a search",
      reset: "Reset",
      queryLabel: "Search question or keywords",
      queryPlaceholder: "What are people saying about romantic date spots in Saigon?",
      queryHint: "Enter a natural question or keywords to search discussions on Threads.",
      keywordsLabel: "Search keywords",
      keywordsPlaceholder: "quiet cafes, reading spots",
      keywordsHint: "Optional. Leave blank to let AI automatically generate optimal keywords.",
      optional: "Optional",
      postsPerKeyword: "Posts per keyword",
      postsPerKeywordHint: "Number of posts to collect per search term (25, 50, 75, or 100 posts).",
      searchOrder: "Search order",
      recent: "Most recent",
      top: "Top posts",
      commentsLabel: "Collect comments",
      commentsDesc: "Read discussions and replies inside collected posts.",
      postsWithComments: "Posts with comments",
      commentsPerPost: "Comments per post",
      minReplies: "Minimum replies to collect",
      presetsTitle: "Quick presets",
      presetBalanced: "Balanced",
      presetBalancedDesc: "15 posts · 25 comments/post",
      presetDeep: "Exhaustive",
      presetDeepDesc: "All comments · full AI curation",
      presetFast: "Quick scan",
      presetFastDesc: "10 posts · top 5 with comments",
      commentsLimit: "Comments per post",
      commentsAll: "All comments (Unlimited)",
      commentsUnlimited: "Unlimited",
      commentsAllNotice: "Automatically scrolls and expands all replies until the discussion is exhausted.",
      postsWithCommentsOption: "Posts with comments",
      postsWithCommentsAll: "All matching posts",
      preFilterStrictness: "AI filter level",
      strictnessNone: "All (No filter)",
      strictnessNoneDesc: "Keep all retrieved posts without AI filtering.",
      strictnessMedium: "Gentle",
      strictnessMediumDesc: "Remove spam and ads, keep relevant or related discussions.",
      strictnessHigh: "Strict",
      strictnessHighDesc: "Only keep posts tightly on topic, excluding indirect discussions.",
      advancedSettings: "Advanced settings",
      hideAdvancedSettings: "Hide advanced settings",
      maxAccountsLabel: "Max accounts to use",
      maxAccountsAll: "All accounts (pool rotation)",
      maxAccountsHint: "Rotate keywords across multiple accounts for faster speed and anti-ban safety.",
      accountUnit: "account",
      accountsUnit: "accounts",
      useProxyLabel: "Enable proxy connection",
      useProxyHint: "Route crawler requests through proxies to protect your network IP.",
      runTimeoutLabel: "Max run timeout",
      runTimeoutHint: "Maximum duration for the full collection before stopping (or until complete).",
      runTimeoutUnlimited: "Until done",
      runTimeoutUnlimitedNotice: "No overall time limit. The selected keyword limit and page loading, result, and stalled-feed checks still apply.",
      searchTimeoutLabel: "Search timeout per keyword",
      searchTimeoutHint: "Limit search time per keyword, or select Until done to remove the time limit.",
      delaysLabel: "Request pacing delay",
      delaysHint: "Random delay between actions to avoid rate limits and anti-bot blocks.",
      delaysFast: "Fast (1s – 2s)",
      delaysNormal: "Normal (2s – 4s)",
      delaysSafe: "Safe (4s – 8s)",
      minRepliesHint: "Only collect comments for posts with at least this many replies.",
      maxCommentPostsHint: "Max posts to extract comments from (top replied posts prioritized, -1 for all).",
      aiTitle: "AI assistance",
      aiUnavailable: "AI features are unavailable. You can still search with your own keywords.",
      expandQuery: "Expand the question",
      expandQueryDesc: "Find short phrases that work well on Threads.",
      keywordsCountLabel: "Number of keywords to extract",
      keywordsCountHint: "AI will extract up to this many optimal 2–3 word search terms (1–5).",
      preFilter: "Filter before collecting comments",
      preFilterDesc: "Skip posts that are unrelated to your question.",
      curate: "Analyze and curate results",
      curateDesc: "Summarize insights and highlight relevant posts.",
      startCollection: "Start collection",
      starting: "Starting collection…",
      cancel: "Cancel collection",
      welcomeTitle: "Start a Threads collection",
      welcomeDesc: "Enter your research question and collection parameters to retrieve discussions.",
      historyTitle: "Collection history",
      emptyHistory: "Your collections will appear here.",
      exportJSON: "Export JSON",
      eyebrow: "SOCIAL INTELLIGENCE",
      configured: "Configured",
      setupRequired: "Setup required",
      newCollection: "New collection",
      fromConversationToContext: "FROM CONVERSATION TO CONTEXT",
      welcomeHeading: "Find the signal in the thread.",
      welcomeSubtitle: "Search a topic, collect the discussion, and let AI help you make sense of it.",
      step1: "Ask a question",
      step2: "Collect conversations",
      step3: "Explore insights",
      reuseSettings: "Reuse settings",
      collectionProgress: "Collection progress",
      backgroundNotice: "Your collection runs in the background. You can return to this page at any time.",
      cancelCollection: "Cancel collection",
      cancelling: "Cancelling…",
      cancelledNotice: "This collection was cancelled. Reuse its settings to start a new one.",
      failedNotice: "This collection could not be completed.",
      collectionResults: "Collection results",
      exportJson: "JSON",
      exportTxt: "Text",
      postsCollected: "Posts collected",
      comments: "Comments",
      curatedPosts: "Curated posts",
      collectionTime: "Collection time",
      filterSearchPlaceholder: "Search within results…",
      curatedOnly: "Curated only",
      postsShown: "posts shown",
      noPostsTitle: "No posts to show",
      noPostsFiltered: "Try a different filter or turn off curated only.",
      noPostsEmpty: "Try broader keywords or a different search order.",
      likes: "likes",
      replies: "replies",
      reposts: "reposts",
      mediaItems: "media items",
      relevant: "Relevant",
      lowerRelevance: "Lower relevance",
      collectedComments: "collected comments",
      replyingTo: "replying to",
      openPost: "Open post",
      noCaption: "This post contains media without a text caption.",
      historyHeading: "Collection history",
      activeSearches: "active",
      savedSearches: "Saved searches",
      loadingHistory: "Loading history…",
      emptyHistoryHint: "Your collections will appear here. Start with a question on the left.",
      loadMoreCollections: "Load more collections",
      loading: "Loading…",
      stages: {
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
      },
    },
    research: {
      heading: "AI Research Tool",
      subheading: "Explore scientific literature with explainable retrieval and multimodal summaries.",
      searchPlaceholder: "Research question (e.g. Explainable multimodal deepfake detection)",
      searchButton: "Search papers",
      searching: "Searching papers…",
      advancedSettings: "Advanced settings",
      hideAdvancedSettings: "Hide advanced settings",
      paperLimits: "arXiv raw papers",
      timeRange: "Time range",
      allTime: "All time",
      from2025: "2025 to present",
      from2024: "2024 to present",
      from2023: "2023 to present",
      customRange: "Custom year range",
      historyTitle: "Research sessions",
      newSession: "New research",
      emptyHistory: "Your research sessions will appear here.",
      downloadPDF: "Download PDF",
      openPDF: "Open PDF",
      renameSession: "Rename",
      deleteSession: "Delete",
      breadcrumb: "AI Research Tool",
      quote: "“Research today, a smarter tomorrow.”",
      searchCardTitle: "Search papers",
      searchCardDesc: "Use a focused research question for better results.",
      sourcesLegend: "Sources",
      maxResults: "Max results",
      papersCount: "papers",
      visibility: "Visibility",
      public: "Public",
      private: "Private",
      customYearsTitle: "Custom Publication Window",
      customYearsDesc: "Specify the publication range for retrieved papers",
      yearFrom: "Year from",
      yearTo: "Year to",
      minYear: "Minimum",
      maxYear: "Maximum",
      candidateExtractionLimits: "Candidate Extraction Limits",
      candidateExtractionDesc: "Set the maximum raw candidate papers to retrieve from each source before AI ranking.",
      resetDefaults: "Reset defaults",
      loadOlder: "Load older sessions",
      startSession: "Start a research session",
      startSessionDesc: "Your search will be queued immediately and remain available after you close this page.",
      loadingSession: "Loading research session…",
      searchResults: "Search results",
      papersShown: "papers",
      sortBy: "Sort by",
      relevance: "Relevance",
      newest: "Newest",
      citations: "Most cited",
      title: "Title",
      filters: "Filters",
      clear: "Clear",
      pubYear: "Publication year",
      allYears: "All years",
      source: "Source",
      allSources: "All sources",
      paperType: "Paper type",
      allTypes: "All types",
      topic: "Topic",
      allTopics: "All topics",
      priority: "Read priority",
      allPriorities: "All priorities",
      high: "High",
      medium: "Medium",
      low: "Low",
      openAccessOnly: "Open access only",
      noPapersMatch: "No papers match these filters",
      clearFilters: "Clear filters",
      open: "Open ↗",
      unavailable: "Unavailable",
      openAccessBadge: "Open access",
      citationsCount: "citations",
      aiSummary: "AI summary",
      abstractBasis: "Analysis based on the abstract.",
      whyReadThis: "Why read this?",
      deleteTitle: "Delete research session",
      deleteConfirm: "Are you sure you want to delete this session? This action cannot be undone and will permanently remove this session and its retrieved papers from your history.",
      deleteButton: "Delete session",
      cancelButton: "Cancel",
    },
    admin: {
      heading: "User Management",
      subheading: "Create accounts and control access to the internal workspace.",
      searchPlaceholder: "Search by name, username, or team…",
      newUser: "New User",
      editUser: "Edit user",
      createUser: "Create user",
      username: "Username",
      displayName: "Display name",
      role: "Role",
      team: "Team",
      status: "Status",
      actions: "Actions",
      deactivate: "Deactivate",
      activate: "Activate",
      edit: "Edit",
      closeDialog: "Close dialog",
      eyebrow: "Administration",
      createEyebrow: "Account provisioning",
      createTitle: "Create user",
      createDesc: "Set up a secure workspace account and assign its initial access level.",
      editEyebrow: "Account administration",
      editTitle: "Edit user",
      editDesc: "Update this member's workspace profile and access level.",
      passwordEyebrow: "Account security",
      passwordTitle: "Reset password",
      passwordDesc: "Set a new temporary password and revoke this user's existing sessions.",
      required: "Required",
      optional: "Optional",
      usernameHint: "3–64 characters, no spaces. Use letters, numbers, dots, underscores, or hyphens.",
      displayNameHint: "The name shown to teammates.",
      teamHint: "Optional organizational group.",
      member: "Member",
      administrator: "Administrator",
      roleHint: "Administrators can manage all accounts.",
      tempPassword: "Temporary password",
      tempPasswordHint: "Use 8–128 characters.",
      notebooklmEmail: "Preferred NotebookLM email",
      notebooklmHint: "Optional. The user must sign in to this Google account in their extension before importing.",
      cancel: "Cancel",
      creating: "Creating…",
      saveChanges: "Save changes",
      saving: "Saving…",
      updatePassword: "Update password",
      updating: "Updating…",
      newTempPassword: "New temporary password",
      newTempPasswordHint: "Use 8–128 characters. All existing tokens for this user will be invalidated.",
      password: "Password",
      selfRoleHint: "Use another administrator account to change your role.",
      search: "Search",
      searching: "Searching…",
      created: "Created",
      emptyTitle: "No users found",
      emptyDesc: "Try another search or create a new account.",
      usersCount: "users",
      userCount: "user",
      previous: "Previous",
      next: "Next",
      pageOf: "Page",
      confirmDeactivate: "Deactivate",
      confirmActivate: "Activate",
      active: "Active",
      inactive: "Inactive",
    },
  },
  vi: {
    nav: {
      home: "Trang chủ",
      research: "Công cụ Nghiên cứu AI",
      threads: "Thu thập Threads",
      datasets: "Tập dữ liệu",
      experiments: "Thử nghiệm",
      monitoring: "Giám sát",
      documents: "Tài liệu",
      users: "Quản lý Người dùng",
      soon: "Sắp có",
      collapse: "Thu gọn thanh điều hướng",
      expand: "Mở rộng thanh điều hướng",
    },
    auth: {
      welcomeBack: "Chào mừng trở lại",
      subtitle: "Đăng nhập vào nền tảng nội bộ CyVerse",
      username: "Tên đăng nhập",
      password: "Mật khẩu",
      usernamePlaceholder: "Tên đăng nhập",
      passwordPlaceholder: "Mật khẩu",
      usernameHint: "Chữ cái, số, dấu chấm, gạch ngang hoặc gạch dưới.",
      show: "Hiện",
      hide: "Ẩn",
      signIn: "Đăng nhập",
      signingIn: "Đang đăng nhập…",
      needAccount: "Chưa có tài khoản? Liên hệ quản trị viên.",
    },
    topbar: {
      platform: "Nền tảng",
      tools: "Công cụ",
      admin: "Quản trị hệ thống",
      account: "Tài khoản",
      searchPlaceholder: "Tìm kiếm trong CyVerse...",
      toggleTheme: "Chuyển giao diện sáng/tối",
      toggleLanguage: "Chuyển đổi ngôn ngữ",
      lightMode: "Giao diện sáng",
      darkMode: "Giao diện tối",
    },
    account: {
      settings: "Cài đặt tài khoản",
      profileSecurity: "Hồ sơ & bảo mật",
      userManagement: "Quản lý người dùng",
      manageAccounts: "Quản lý tài khoản & phân quyền",
      signOut: "Đăng xuất",
      endSession: "Kết thúc phiên làm việc",
      signingOut: "Đang đăng xuất…",
      adminRole: "Quản trị viên",
      memberRole: "Thành viên",
    },
    dashboard: {
      greeting: "Xin chào",
      subtitle: "Bộ công cụ nội bộ bảo mật cho AI có thể giải thích và truyền thông tin cậy.",
      overview: "Tổng quan nền tảng",
      availableTools: "Công cụ khả dụng",
      launchTool: "Mở công cụ",
      recentActivity: "Hoạt động gần đây",
      deepfakeTitle: "Phát hiện Deepfake",
      deepfakeDesc: "Phát hiện hình ảnh và video bị chỉnh sửa bằng AI có thể giải thích.",
      videoTitle: "Phân tích Video",
      videoDesc: "Phân tích nội dung video, trích xuất khung hình chính và dữ liệu.",
      explainTitle: "Trực quan hóa mô hình",
      explainDesc: "Hiển thị giải thích mô hình và bản đồ chú ý (attention maps).",
      datasetTitle: "Quản lý tập dữ liệu",
      datasetDesc: "Quản lý, xem trước và dán nhãn các tập dữ liệu huấn luyện.",
      activeRuns: "Tác vụ đang chạy",
      systemStatus: "Trạng thái hệ thống",
      connectedAPIs: "API đã kết nối",
      demoPill: "Dữ liệu mẫu",
      tagline: "Cùng xây dựng, thử nghiệm và triển khai giải pháp phát hiện deepfake có thể giải thích được.",
      quote: "“Truyền thông đáng tin cậy hơn cho một ngày mai an toàn hơn.”",
      quoteAuthor: "— CyVerse",
      availableToolsMetric: "Công cụ khả dụng",
      datasetsMetric: "Tập dữ liệu",
      experimentsMetric: "Thử nghiệm",
      teamMembersMetric: "Thành viên nhóm",
      popularTools: "Công cụ phổ biến",
      popularToolsSubtitle: "Được chọn lọc cho đội ngũ của bạn",
      comingSoon: "Sắp ra mắt",
      noToolsFound: "Không tìm thấy công cụ nào",
      noToolsDesc: "Thử tìm kiếm với từ khóa khác.",
      sampleActivity: "Hoạt động mẫu",
      activityItemTitle: "Phân tích Phát hiện Deepfake đã hoàn thành",
      activityItemMeta: "Video mẫu · 2 giờ trước",
      completed: "Đã hoàn thành",
      adminRequiredNotice: "Cần có quyền Quản trị viên để truy cập Quản lý Người dùng.",
    },
    settings: {
      eyebrow: "Không gian làm việc cá nhân",
      heading: "Cài đặt tài khoản",
      subheading: "Quản lý thông tin cá nhân và bảo mật tài khoản của bạn.",
      role: "Vai trò",
      team: "Đội ngũ / Nhóm",
      status: "Trạng thái",
      active: "Đang hoạt động",
      inactive: "Đã vô hiệu hóa",
      notAssigned: "Chưa phân công",
      profileHeading: "Thông tin hồ sơ",
      profileSubheading: "Thông tin này hiển thị trên toàn bộ không gian làm việc của bạn.",
      username: "Tên đăng nhập",
      usernameHint: "Tên đăng nhập là cố định và do quản trị viên quản lý.",
      displayName: "Tên hiển thị",
      displayNameHint: "Sử dụng tên giúp đồng đội dễ nhận diện bạn.",
      displayNamePlaceholder: "ví dụ: CyVerse",
      teamHint: "Tùy chọn. Giúp đồng đội biết bạn làm việc ở nhóm nào.",
      teamPlaceholder: "ví dụ: Nền tảng Dữ liệu",
      notebooklmEmail: "Email NotebookLM ưu tiên",
      notebooklmHint: "Kết nối tài khoản Google này trong tiện ích trước khi nhập bài báo. Có thể đổi bất cứ lúc nào.",
      saveProfile: "Lưu hồ sơ",
      saving: "Đang lưu…",
      securityHeading: "Mật khẩu & bảo mật",
      securitySubheading: "Đổi mật khẩu sẽ đăng xuất bạn khỏi tất cả các thiết bị và phiên làm việc khác.",
      currentPassword: "Mật khẩu hiện tại",
      currentPasswordPlaceholder: "Nhập mật khẩu hiện tại",
      newPassword: "Mật khẩu mới",
      newPasswordPlaceholder: "Tối thiểu 8 ký tự",
      confirmPassword: "Xác nhận mật khẩu",
      confirmPasswordPlaceholder: "Nhập lại mật khẩu mới",
      passwordHint: "Dùng từ 8–128 ký tự và tránh sử dụng lại mật khẩu cũ.",
      updatePassword: "Cập nhật mật khẩu",
      updating: "Đang cập nhật…",
    },
    threads: {
      tabScraper: "Thu thập Threads",
      tabTravel: "Địa điểm du lịch",
      travelHeading: "Khám phá Địa điểm & Du lịch",
      travelSubheading: "Chuyên trang tìm kiếm quán ăn, quán cà phê và địa điểm du lịch ít người biết qua thảo luận thực tế trên Threads.",
      travelEyebrow: "KHÁM PHÁ ĐỊA ĐIỂM DU LỊCH",
      travelCityLabel: "Điểm đến phổ biến",
      travelCategoryLabel: "Chủ đề quan tâm",
      travelQueryPlaceholder: "ví dụ: Các quán ăn ngon, quán cafe yên tĩnh ít người biết quanh TP. Hồ Chí Minh...",
      travelPreviewBadge: "Chế độ chuyên biệt",
      travelPreviewNotice: "Giao diện chế độ Chuyên biệt Du lịch — Tối ưu trích xuất địa điểm, quán ăn ẩn và đánh giá thực tế từ người dân địa phương.",
      searchBoth: "Cả 2 chế độ (Gần đây & Phổ biến)",
      travelPromptLabel: "Nhập Prompt chủ đề / địa điểm cần cào",
      travelPromptPlaceholder: "Nhập yêu cầu hoặc chủ đề (Ví dụ: Tìm các quán ăn vặt, quán ốc, cafe chill quanh Sài Gòn ít người biết...)",
      analyzeKeywordsBtn: "Phân tích Keyword (AI)",
      analyzingKeywords: "Đang phân tích...",
      analyzedKeywordsTitle: "Từ khóa cào dữ liệu được phân tích",
      analyzedKeywordsHint: "Hệ thống sẽ chạy đồng thời cả 2 chế độ (Gần đây + Phổ biến nhất) cho từng keyword này.",
      addKeywordPlaceholder: "Thêm từ khóa tự chọn...",
      dualModeTitle: "Chế độ tìm kiếm",
      dualModeBadge: "Chạy cả 2 chế độ: Gần đây & Phổ biến nhất (Mặc định)",
      dedupBadge: "Luôn kiểm tra & Lọc trùng lặp bài viết (Bắt buộc)",
      dedupNotice: "Tự động đối chiếu ID bài viết, URL và lịch sử để loại bỏ mọi bài viết trùng lặp giữa các keyword và giữa 2 chế độ tìm kiếm.",
      continuousTitle: "Treo tool cào data liên tục",
      continuousBadge: "Chế độ treo tool cào dữ liệu",
      startCrawlerBtn: "Bắt đầu cào dữ liệu liên tục",
      dedupFilteredCount: "Bài trùng lặp đã loại bỏ",
      uniquePostsCount: "Bài viết duy nhất",
      groupedKeywordsTitle: "Nhóm từ khóa AI đề xuất",
      groupedKeywordsDesc: "AI đã phân tích prompt và phân loại các từ khóa theo nhóm chủ đề để tối ưu phạm vi cào dữ liệu.",
      selectAllInGroup: "Chọn tất cả",
      deselectAllInGroup: "Bỏ chọn",
      addKeywordToGroup: "Thêm từ khóa vào nhóm",
      addKeywordGroup: "Thêm nhóm chủ đề",
      newGroupName: "Tên nhóm chủ đề mới...",
      selectedKeywordsSummary: "Từ khóa được chọn để cào",
      noKeywordsSelected: "Chưa chọn từ khóa nào. Hãy chọn hoặc thêm ít nhất 1 từ khóa.",
      removeGroup: "Xóa nhóm",
      heading: "Thu thập Threads",
      subheading: "Thu thập, phân tích và xuất dữ liệu Threads công khai với hỗ trợ của AI.",
      configTitle: "Cấu hình tìm kiếm",
      reset: "Đặt lại",
      queryLabel: "Câu hỏi tìm kiếm hoặc từ khóa",
      queryPlaceholder: "Mọi người đang nói gì về địa điểm hẹn hò lãng mạn ở Sài Gòn?",
      queryHint: "Nhập câu hỏi tự nhiên hoặc từ khóa cần tìm kiếm thảo luận trên Threads.",
      keywordsLabel: "Từ khóa tìm kiếm",
      keywordsPlaceholder: "quán cà phê yên tĩnh, điểm đọc sách",
      keywordsHint: "Tùy chọn. Để trống để AI tự động trích xuất các từ khóa tối ưu.",
      optional: "Tùy chọn",
      postsPerKeyword: "Số bài viết mỗi từ khóa",
      postsPerKeywordHint: "Số bài viết cần thu thập cho mỗi từ khóa (25, 50, 75 hoặc 100 bài).",
      searchOrder: "Thứ tự tìm kiếm",
      recent: "Mới nhất",
      top: "Bài viết nổi bật",
      commentsLabel: "Thu thập bình luận",
      commentsDesc: "Đọc thêm các thảo luận và phản hồi trong từng bài viết.",
      postsWithComments: "Bài viết kèm bình luận",
      commentsPerPost: "Bình luận mỗi bài viết",
      minReplies: "Số phản hồi tối thiểu để thu thập",
      presetsTitle: "Cấu hình nhanh",
      presetBalanced: "Tiêu chuẩn",
      presetBalancedDesc: "15 bài · 25 bình luận/bài",
      presetDeep: "Toàn diện",
      presetDeepDesc: "Lấy tất cả bình luận · phân tích AI",
      presetFast: "Nhanh gọn",
      presetFastDesc: "10 bài · 5 bài có bình luận",
      commentsLimit: "Số lượng bình luận mỗi bài",
      commentsAll: "Tất cả bình luận (Không giới hạn)",
      commentsUnlimited: "Không giới hạn",
      commentsAllNotice: "Tự động cuộn và bấm mở rộng mọi phản hồi cho tới khi hết thảo luận.",
      postsWithCommentsOption: "Số bài viết lấy bình luận",
      postsWithCommentsAll: "Tất cả bài viết phù hợp",
      preFilterStrictness: "Mức độ lọc của AI",
      strictnessNone: "Lấy tất cả",
      strictnessNoneDesc: "Lấy tất cả bài viết tìm được mà không cần AI lọc.",
      strictnessMedium: "Lọc nhẹ nhàng",
      strictnessMediumDesc: "Lọc bỏ quảng cáo và spam, giữ lại các thảo luận liên quan hoặc mở rộng.",
      strictnessHigh: "Lọc mạnh",
      strictnessHighDesc: "Chỉ giữ bài viết bám sát 100% câu hỏi, loại bỏ thảo luận gián tiếp.",
      advancedSettings: "Cài đặt nâng cao",
      hideAdvancedSettings: "Ẩn cài đặt nâng cao",
      maxAccountsLabel: "Số tài khoản tối đa để chạy",
      maxAccountsAll: "Tất cả tài khoản (xoay vòng pool)",
      maxAccountsHint: "Phân bổ luân phiên các từ khóa qua nhiều tài khoản để tăng tốc độ và tránh bị chặn.",
      accountUnit: "tài khoản",
      accountsUnit: "tài khoản",
      useProxyLabel: "Bật kết nối qua Proxy",
      useProxyHint: "Định tuyến lưu lượng cào qua proxy để bảo vệ địa chỉ IP và tránh giới hạn mạng.",
      runTimeoutLabel: "Thời gian chạy tối đa",
      runTimeoutHint: "Thời gian tối đa cho toàn bộ tác vụ trước khi dừng (hoặc đến khi cào xong).",
      runTimeoutUnlimited: "Đến khi xong",
      runTimeoutUnlimitedNotice: "No overall time limit. The selected keyword limit and page loading, result, and stalled-feed checks still apply.",
      searchTimeoutLabel: "Thời gian tìm kiếm mỗi từ khóa",
      searchTimeoutHint: "Limit search time per keyword, or select Until done to remove the time limit.",
      delaysLabel: "Độ trễ giữa các lượt cào",
      delaysHint: "Khoảng nghỉ ngẫu nhiên giữa các thao tác để tránh bị chặn hoặc giới hạn tốc độ.",
      delaysFast: "Nhanh (1s – 2s)",
      delaysNormal: "Tiêu chuẩn (2s – 4s)",
      delaysSafe: "An toàn (4s – 8s)",
      minRepliesHint: "Chỉ thu thập bình luận cho các bài viết có ít nhất số phản hồi này.",
      maxCommentPostsHint: "Số bài viết tối đa cần lấy bình luận (ưu tiên bài nhiều phản hồi nhất, -1 là tất cả).",
      aiTitle: "Hỗ trợ bởi AI",
      aiUnavailable: "Tính năng AI tạm thời không khả dụng. Bạn vẫn có thể tìm kiếm với từ khóa của mình.",
      expandQuery: "Mở rộng câu hỏi",
      expandQueryDesc: "Tìm các cụm từ ngắn hoạt động hiệu quả trên Threads.",
      keywordsCountLabel: "Số từ khóa mở rộng",
      keywordsCountHint: "AI sẽ sinh ra tối đa số lượng từ khóa 2–3 từ tối ưu này (1–5 từ khóa).",
      preFilter: "Lọc trước khi thu thập bình luận",
      preFilterDesc: "Bỏ qua các bài viết không liên quan đến câu hỏi của bạn.",
      curate: "Phân tích và chọn lọc kết quả",
      curateDesc: "Tổng hợp thông tin chi tiết và làm nổi bật các bài viết phù hợp.",
      startCollection: "Bắt đầu thu thập",
      starting: "Đang bắt đầu thu thập…",
      cancel: "Hủy thu thập",
      welcomeTitle: "Bắt đầu thu thập dữ liệu Threads",
      welcomeDesc: "Nhập câu hỏi nghiên cứu và các tham số cấu hình để bắt đầu thu thập thảo luận.",
      historyTitle: "Lịch sử thu thập",
      emptyHistory: "Các phiên thu thập của bạn sẽ xuất hiện ở đây.",
      exportJSON: "Xuất file JSON",
      eyebrow: "THÔNG TIN MẠNG XÃ HỘI",
      configured: "Đã cấu hình",
      setupRequired: "Cần thiết lập",
      newCollection: "Thu thập mới",
      fromConversationToContext: "TỪ THẢO LUẬN ĐẾN THÔNG TIN",
      welcomeHeading: "Khám phá thông điệp cốt lõi từ các chuỗi thảo luận.",
      welcomeSubtitle: "Tìm kiếm chủ đề, thu thập thảo luận và để AI giúp bạn đúc kết thông tin.",
      step1: "Đặt câu hỏi",
      step2: "Thu thập thảo luận",
      step3: "Khám phá phân tích",
      reuseSettings: "Dùng lại cấu hình này",
      collectionProgress: "Tiến trình thu thập",
      backgroundNotice: "Quá trình thu thập chạy dưới nền. Bạn có thể quay lại trang này bất cứ lúc nào.",
      cancelCollection: "Hủy thu thập",
      cancelling: "Đang hủy…",
      cancelledNotice: "Phiên thu thập này đã bị hủy. Hãy dùng lại cấu hình để bắt đầu phiên mới.",
      failedNotice: "Phiên thu thập không thể hoàn tất.",
      collectionResults: "Kết quả thu thập",
      exportJson: "JSON",
      exportTxt: "Văn bản",
      postsCollected: "Bài viết đã thu thập",
      comments: "Bình luận",
      curatedPosts: "Bài viết đã chọn lọc",
      collectionTime: "Thời gian thu thập",
      filterSearchPlaceholder: "Tìm kiếm trong kết quả…",
      curatedOnly: "Chỉ bài đã chọn lọc",
      postsShown: "bài viết được hiển thị",
      noPostsTitle: "Không có bài viết nào",
      noPostsFiltered: "Thử bộ lọc khác hoặc tắt chế độ chỉ bài chọn lọc.",
      noPostsEmpty: "Thử từ khóa rộng hơn hoặc thứ tự tìm kiếm khác.",
      likes: "lượt thích",
      replies: "phản hồi",
      reposts: "lượt đăng lại",
      mediaItems: "mục đa phương tiện",
      relevant: "Phù hợp",
      lowerRelevance: "Độ liên quan thấp",
      collectedComments: "bình luận đã thu thập",
      replyingTo: "trả lời",
      openPost: "Mở bài viết",
      noCaption: "Bài viết này chứa nội dung đa phương tiện không có chú thích chữ.",
      historyHeading: "Lịch sử thu thập",
      activeSearches: "đang chạy",
      savedSearches: "Tìm kiếm đã lưu",
      loadingHistory: "Đang tải lịch sử…",
      emptyHistoryHint: "Các phiên thu thập của bạn sẽ xuất hiện ở đây. Hãy bắt đầu bằng câu hỏi ở bên trái.",
      loadMoreCollections: "Tải thêm các phiên thu thập",
      loading: "Đang tải…",
      stages: {
        queued: "Đang chờ trong hàng đợi",
        planning: "Lập kế hoạch tìm kiếm",
        searching: "Đang thu thập bài viết",
        filtering: "Đang lọc bài viết",
        comments: "Đang thu thập bình luận",
        curating: "Đang phân tích kết quả",
        saving: "Đang lưu kết quả",
        completed: "Thu thập hoàn tất",
        cancelled: "Thu thập đã bị hủy",
        failed: "Thu thập thất bại",
      },
    },
    research: {
      heading: "Công cụ Nghiên cứu AI",
      subheading: "Khám phá tài liệu khoa học với truy xuất có thể giải thích và tóm tắt đa phương thức.",
      searchPlaceholder: "Câu hỏi nghiên cứu (ví dụ: Phát hiện deepfake đa phương thức có thể giải thích)",
      searchButton: "Tìm kiếm bài báo",
      searching: "Đang tìm kiếm bài báo…",
      advancedSettings: "Cấu hình nâng cao",
      hideAdvancedSettings: "Ẩn cấu hình nâng cao",
      paperLimits: "Số bài báo arXiv",
      timeRange: "Khoảng thời gian",
      allTime: "Tất cả thời gian",
      from2025: "2025 đến nay",
      from2024: "2024 đến nay",
      from2023: "2023 đến nay",
      customRange: "Tùy chọn khoảng năm",
      historyTitle: "Phiên nghiên cứu",
      newSession: "Nghiên cứu mới",
      emptyHistory: "Các phiên nghiên cứu của bạn sẽ hiển thị ở đây.",
      downloadPDF: "Tải file PDF",
      openPDF: "Mở PDF",
      renameSession: "Đổi tên",
      deleteSession: "Xóa",
      breadcrumb: "Công cụ Nghiên cứu AI",
      quote: "“Nghiên cứu hôm nay, tương lai thông thái hơn.”",
      searchCardTitle: "Tìm kiếm bài báo",
      searchCardDesc: "Đặt câu hỏi nghiên cứu cụ thể để nhận kết quả chính xác hơn.",
      sourcesLegend: "Nguồn dữ liệu",
      maxResults: "Số kết quả tối đa",
      papersCount: "bài báo",
      visibility: "Chế độ hiển thị",
      public: "Công khai",
      private: "Riêng tư",
      customYearsTitle: "Tùy chọn khoảng năm công bố",
      customYearsDesc: "Chỉ định khoảng thời gian công bố của bài báo cần tìm",
      yearFrom: "Từ năm",
      yearTo: "Đến năm",
      minYear: "Tối thiểu",
      maxYear: "Tối đa",
      candidateExtractionLimits: "Giới hạn trích xuất bài báo thô",
      candidateExtractionDesc: "Đặt số lượng bài báo thô tối đa cần thu thập từ mỗi nguồn trước khi AI xếp hạng.",
      resetDefaults: "Khôi phục mặc định",
      loadOlder: "Tải các phiên cũ hơn",
      startSession: "Bắt đầu phiên nghiên cứu",
      startSessionDesc: "Tìm kiếm của bạn sẽ được đưa vào hàng đợi ngay lập tức và vẫn sẵn sàng khi bạn đóng trang.",
      loadingSession: "Đang tải phiên nghiên cứu…",
      searchResults: "Kết quả tìm kiếm",
      papersShown: "bài báo",
      sortBy: "Sắp xếp theo",
      relevance: "Độ liên quan",
      newest: "Mới nhất",
      citations: "Nhiều trích dẫn nhất",
      title: "Tiêu đề",
      filters: "Bộ lọc",
      clear: "Xóa bộ lọc",
      pubYear: "Năm công bố",
      allYears: "Tất cả các năm",
      source: "Nguồn",
      allSources: "Tất cả các nguồn",
      paperType: "Loại tài liệu",
      allTypes: "Tất cả các loại",
      topic: "Chủ đề",
      allTopics: "Tất cả chủ đề",
      priority: "Mức độ ưu tiên đọc",
      allPriorities: "Tất cả mức độ",
      high: "Cao",
      medium: "Trung bình",
      low: "Thấp",
      openAccessOnly: "Chỉ bài báo mở (Open access)",
      noPapersMatch: "Không có bài báo nào khớp với bộ lọc này",
      clearFilters: "Xóa bộ lọc",
      open: "Mở ↗",
      unavailable: "Không khả dụng",
      openAccessBadge: "Truy cập mở",
      citationsCount: "trích dẫn",
      aiSummary: "Tóm tắt bởi AI",
      abstractBasis: "Phân tích dựa trên phần tóm tắt (abstract).",
      whyReadThis: "Tại sao nên đọc bài này?",
      deleteTitle: "Xóa phiên nghiên cứu",
      deleteConfirm: "Bạn có chắc chắn muốn xóa phiên này? Thao tác này không thể hoàn tác và sẽ xóa vĩnh viễn phiên này cùng các bài báo đã truy xuất khỏi lịch sử.",
      deleteButton: "Xóa phiên",
      cancelButton: "Hủy",
    },
    admin: {
      heading: "Quản lý Người dùng",
      subheading: "Tạo tài khoản và kiểm soát quyền truy cập vào không gian làm việc nội bộ.",
      searchPlaceholder: "Tìm theo tên, tên đăng nhập hoặc đội ngũ…",
      newUser: "Thêm người dùng",
      editUser: "Sửa người dùng",
      createUser: "Tạo người dùng",
      username: "Tên đăng nhập",
      displayName: "Tên hiển thị",
      role: "Vai trò",
      team: "Đội ngũ",
      status: "Trạng thái",
      actions: "Thao tác",
      deactivate: "Vô hiệu hóa",
      activate: "Kích hoạt",
      edit: "Sửa",
      closeDialog: "Đóng cửa sổ",
      eyebrow: "Quản trị hệ thống",
      createEyebrow: "Cấp tài khoản",
      createTitle: "Tạo người dùng",
      createDesc: "Thiết lập tài khoản bảo mật và phân quyền truy cập ban đầu.",
      editEyebrow: "Quản trị tài khoản",
      editTitle: "Chỉnh sửa người dùng",
      editDesc: "Cập nhật hồ sơ và quyền truy cập của thành viên này.",
      passwordEyebrow: "Bảo mật tài khoản",
      passwordTitle: "Đặt lại mật khẩu",
      passwordDesc: "Thiết lập mật khẩu tạm thời mới và thu hồi các phiên đăng nhập hiện tại.",
      required: "Bắt buộc",
      optional: "Tùy chọn",
      usernameHint: "3–64 ký tự, không dấu cách. Dùng chữ cái, số, dấu chấm, gạch dưới hoặc gạch nối.",
      displayNameHint: "Tên hiển thị cho các thành viên trong nhóm.",
      teamHint: "Nhóm hoặc phòng ban trực thuộc.",
      member: "Thành viên",
      administrator: "Quản trị viên",
      roleHint: "Quản trị viên có thể quản lý tất cả tài khoản.",
      tempPassword: "Mật khẩu tạm thời",
      tempPasswordHint: "Dùng từ 8–128 ký tự.",
      notebooklmEmail: "Email NotebookLM ưu tiên",
      notebooklmHint: "Tùy chọn. Người dùng cần đăng nhập vào tài khoản Google này trong tiện ích mở rộng trước khi nhập bài báo.",
      cancel: "Hủy",
      creating: "Đang tạo…",
      saveChanges: "Lưu thay đổi",
      saving: "Đang lưu…",
      updatePassword: "Cập nhật mật khẩu",
      updating: "Đang cập nhật…",
      newTempPassword: "Mật khẩu tạm thời mới",
      newTempPasswordHint: "Dùng từ 8–128 ký tự. Tất cả phiên đăng nhập trước đó của người dùng này sẽ bị hủy bỏ.",
      password: "Mật khẩu",
      selfRoleHint: "Dùng tài khoản quản trị viên khác để thay đổi vai trò của bạn.",
      search: "Tìm kiếm",
      searching: "Đang tìm…",
      created: "Ngày tạo",
      emptyTitle: "Không tìm thấy người dùng",
      emptyDesc: "Thử tìm kiếm khác hoặc tạo tài khoản mới.",
      usersCount: "người dùng",
      userCount: "người dùng",
      previous: "Trước",
      next: "Sau",
      pageOf: "Trang",
      confirmDeactivate: "Vô hiệu hóa",
      confirmActivate: "Kích hoạt",
      active: "Đang hoạt động",
      inactive: "Đã vô hiệu hóa",
    },
  },
};
