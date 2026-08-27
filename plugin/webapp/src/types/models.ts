export type Intent = 'factual' | 'live_status' | 'policy' | 'decision' | 'restricted';
export type RunStatus = 'running' | 'answered' | 'escalated' | 'refused' | 'failed';
export type DecisionStatus = 'pending' | 'approved' | 'rejected' | 'discuss';

export interface Availability {
    status: string;
    until: string | null;
    delegate_user_id: string | null;
}

export interface User {
    id: string;
    name: string;
    title: string;
    team_ids: string[];
    roles: string[];
    project_ids: string[];
    availability: Availability;
    avatar: string;
}

export interface Project {
    id: string;
    name: string;
    summary: string;
    owner_user_id: string;
    team_ids: string[];
    status: string;
    health: string;
    blocker_ids: string[];
    target_date: string;
}

export interface Evidence {
    id: string;
    title: string;
    source_type: string;
    source_url: string;
    entity_ids: string[];
    scope: string;
    content: string;
    observed_at: string;
    confidence: number;
    security_state: 'trusted' | 'blocked';
    security_reason?: string | null;
}

export interface RouteStep {
    ordinal: number;
    delegate_id: string;
    delegate_name: string;
    reason: string;
    outcome: string;
    duration_ms: number;
}

export interface SecurityFinding {
    evidence_id: string;
    category: string;
    severity: string;
    reason: string;
    blocked: boolean;
}

export interface QueryResult {
    run_id: string;
    requester_id: string;
    query: string;
    intent: Intent;
    status: RunStatus;
    answer: string;
    headline: string;
    route: RouteStep[];
    evidence: Evidence[];
    confidence: number;
    freshness_label: string;
    people_interrupted: number;
    decision_id?: string | null;
    decision_assignee_id?: string | null;
    policy_result?: string | null;
    security_findings: SecurityFinding[];
    created_at: string;
    completed_at: string;
    cached: boolean;
    model_name?: string | null;
    model_calls: number;
    model_input_tokens: number;
    model_output_tokens: number;
    model_cached_input_tokens: number;
}

export interface DecisionOption {
    id: string;
    label: string;
    tone: 'positive' | 'negative' | 'neutral';
}

export interface Decision {
    id: string;
    canonical_key: string;
    title: string;
    summary: string;
    requester_id: string;
    assignee_id: string;
    project_id?: string | null;
    status: DecisionStatus;
    options: DecisionOption[];
    evidence_ids: string[];
    policy_ids: string[];
    created_at: string;
    due_at?: string | null;
    resolved_at?: string | null;
    resolved_by?: string | null;
    rationale?: string | null;
}

export interface SemanticWorkState {
    entity_id: string;
    entity_type: 'person' | 'project' | 'team' | 'work_item';
    headline: string;
    detail: string;
    status: string;
    confidence: number;
    source_event_ids: string[];
    updated_at: string;
}

export interface BootstrapResponse {
    current_user: User;
    projects: Project[];
    needs_you: Decision[];
    work_states: SemanticWorkState[];
    attention_metrics: Record<string, number>;
}

export interface Delegate {
    id: string;
    name: string;
    kind: 'personal' | 'project' | 'team' | 'policy' | 'router' | 'authority';
    entity_id: string;
    capabilities: string[];
    data_scopes: string[];
    owner_user_id?: string | null;
    status: string;
}

export interface RegistryResponse {
    delegates: Delegate[];
    relationships: Array<{from: string; type: string; to: string}>;
}

export interface AuditEvent {
    id: string;
    event_type: string;
    actor_id: string;
    entity_ids: string[];
    summary: string;
    created_at: string;
    metadata: Record<string, unknown>;
}


export interface HealthResponse {
    status: string;
    mode: string;
    ai_enabled: boolean;
    version: string;
}

export interface MetricsResponse {
    queries_total: number;
    resolved_without_human: number;
    human_interruptions: number;
    restricted_requests_blocked: number;
    poisoned_sources_blocked: number;
    cache_hits: number;
    model_usage_day: number;
    model_calls: number;
    model_input_tokens: number;
    model_output_tokens: number;
    model_cached_input_tokens: number;
    model_budget_blocks: number;
    active_runs: number;
    delegates: number;
    decision_memories: number;
}
