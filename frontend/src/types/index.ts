export interface Profile {
  id: number;
  name: string;
  is_active: boolean;
  target_queries: string[];
  target_locations: string[];
  resume_pdf_path?: string;
  evaluator_prompt?: string | null;
  created_at: string;
}

export interface Job {
  id: number;
  profile_id: number;
  job_title: string;
  company_name: string;
  job_url: string;
  location: string | null;
  source: string | null;
  job_description: string | null;
  match_score: number | null;
  match_reasoning: string | null;
  cover_letter: string | null;
  apply_links: { title: string; link: string }[] | null;
  application_status: string;
  search_query: string | null;
  date_added: string;
  date_evaluated: string | null;
}

export interface ScrapeResult {
  profile_id: number;
  profile_name: string;
  total_found: number;
  new_inserted: number;
  skipped: number;
}

export interface EvaluateResult {
  profile_id: number;
  profile_name: string;
  jobs_evaluated: number;
  avg_score: number;
}
