export interface AccountRecord {
  did: string;
  handle: string;
  alias: string; // e.g. "A-7F3A2B"
  createdAt: string | null; // ISO timestamp from plc.directory or getProfile
  firstSeen: string; // ISO timestamp
  enriched: boolean;
  enrichStatus?: string;
  enrichAttempts?: number;
}

export interface PostRecord {
  id: string;
  did: string;
  text: string;
  textNorm: string;
  createdAt: string; // ISO timestamp
  topicId: number;
  links: string[];
  hashtags: string[];
  source?: 'demo' | 'live' | 'recorded';
  authorAlias?: string;
  authorHandle?: string;
  authorCreatedAt?: string | null;
}

export interface SignalPair {
  didA: string;
  didB: string;
  strength: number; // 0.0 to 1.0
  reason: string;
  signalType: 'text' | 'timing' | 'age' | 'links';
}

export interface SignalBreakdown {
  text: number;   // 0..1
  timing: number; // 0..1
  age: number;    // 0..1
  links: number;  // 0..1
}

export interface ClusterResult {
  id: string;
  topicId: number;
  score: number; // 0 to 100
  rawScore: number; // before false-positive discount
  discountApplied: number; // e.g. 0.35 if organic news-share discount applied
  discountReason: string | null;
  classification?: 'coordinated_inauthentic' | 'coordinated_benign' | 'organic' | 'insufficient_evidence' | null;
  benignChecks?: Record<string, boolean>;
  significance?: {
    p_value: number | null;
    status?: 'tested' | 'not_tested';
    n_permutations?: number;
    fdr_q_value?: number | null;
    significant?: boolean;
    fdr_significant?: boolean;
    stat_observed?: number;
    reason?: string;
  };
  size: number;
  memberDids: string[];
  members: {
    did: string;
    alias: string;
    handle: string;
    createdAt: string | null;
    postCount: number;
    nodeScore: number;
  }[];
  signals: SignalBreakdown;
  reasons: string[];
  examplePosts: {
    id: string;
    did: string;
    alias: string;
    handle: string;
    text: string;
    textNorm?: string;
    createdAt: string;
    links?: string[];
    hashtags?: string[];
  }[];
  computedAt: string;
}

export interface GraphNode {
  id: string; // DID
  alias: string;
  handle?: string;
  clusterId?: string | null;
  cluster?: string;
  label?: string;
  score: number; // 0 to 100
  postCount?: number;
  createdAt?: string | null;
}

export interface GraphLink {
  source: string;
  target: string;
  weight: number;
  dominantSignal?: 'text' | 'timing' | 'age' | 'links';
  reason?: string;
  signals?: SignalBreakdown | string[];
}

export interface NetworkGraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

export type GraphData = NetworkGraphData;

export interface TimelineBucket {
  label: string;
  total: number;
  flagged: number;
  bucket?: string;
  timestamp?: number;
  totalPosts?: number;
  flaggedPosts?: number;
  coordinatedPosts?: number;
  organicPosts?: number;
  phaseLabel?: 'Seeding' | 'Amplification' | 'Sustained';
}

export interface EvasionPoint {
  level: string;
  intensity: number;
  textParaphraseF1: number;
  timingDelayF1?: number;
  randomDelayF1?: number;
  ageSpreadF1: number;
  linkRotationF1: number;
}

export type EvasionRow = EvasionPoint;

export interface PlantedBotNetSummary {
  id?: string;
  name: string;
  tactic?: string;
  plantedAccounts?: number;
  detectedAccounts?: number;
  botCount?: number;
  detected?: number;
  precision: number;
  recall: number;
  f1?: number;
  meanClusterScore?: number;
}

export type NetworkBreakdown = PlantedBotNetSummary;

export interface FalsePositiveStress {
  scenario?: string;
  organicNewsAccounts?: number;
  organicUsersCount?: number;
  sharedHeadline?: string;
  rawFlaggedWithoutProtection: number;
  flaggedWithProtection: number;
  falsePositiveRateBefore: number;
  falsePositiveRateAfter: number;
  explanation?: string;
}

export interface EvaluationReport {
  status?: string;
  detail?: string;
  label?: string;
  splitDescription?: string;
  computedAt: string;
  totalAccounts?: number;
  organicAccounts?: number;
  plantedBotAccounts?: number;
  truePositives: number;
  falsePositives: number;
  falseNegatives: number;
  trueNegatives?: number;
  precision: number;
  recall: number;
  f1: number;
  baseline?: {
    precision: number;
    recall: number;
    f1: number;
    tp: number;
    fp: number;
    fn: number;
    tn: number;
  };
  plantedNetworks?: PlantedBotNetSummary[];
  networkBreakdown?: PlantedBotNetSummary[];
  evasionCurve?: EvasionPoint[];
  falsePositiveStress?: FalsePositiveStress;
  falsePositiveStressTest?: FalsePositiveStress;
  honestLimitations?: any[];
  multiSeedSummary?: {
    seeds: number[];
    meanPrecision: number;
    meanRecall: number;
    meanF1: number;
    date: string;
  };
  devSummary?: any;
  testSummary?: any;
  nullControl?: any;
  baselines?: any;
  ablations?: any;
  evasionBoundaries?: any[];
  hardNegatives?: any;
}

export type EvaluationResult = EvaluationReport;

export interface TopicInfo {
  id: number;
  keyword: string;
  mode?: string;
  source?: 'demo' | 'live' | 'recorded' | string;
  postCount: number;
  accountCount: number;
  clusterCount: number;
  highRiskCount?: number;
  highRiskClusterCount?: number;
  createdAt?: string;
  startedAt?: string;
  lastAnalyzedAt?: string;
}

export interface ClusterDetail extends ClusterResult {
  coordinationScore?: number;
  riskBand?: string;
  memberCount?: number;
  evidence?: string[];
  topPhrases?: string[];
  topDomains?: string[];
  activitySparkline?: number[];
}

export function clusterClassLabel(value?: string | null): string {
  switch (value) {
    case 'coordinated_inauthentic':
      return 'Inauthentic';
    case 'coordinated_benign':
      return 'Benign';
    case 'organic':
      return 'Organic';
    case 'insufficient_evidence':
      return 'Insufficient evidence';
    default:
      return 'unlabeled';
  }
}
