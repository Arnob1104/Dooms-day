export interface Movie {
  id: number;
  title: string;
  release_year: number;
  runtime_minutes: number;
  watched: boolean;
  prerequisite_ids: number[];
}

export interface RewatchItem {
  id: number;
  title: string;
  release_year: number;
  runtime_minutes: number;
  watched: boolean;
}

export interface RewatchPlan {
  movie_id: number;
  movie_title: string;
  order: RewatchItem[];
  total_count: number;
  watched_count: number;
  remaining_runtime_minutes: number;
}

export interface Cinema {
  id: number;
  name: string;
  bundle_sizes: number[];
}

export interface BundleCount {
  size: number;
  count: number;
}

export interface BookingQuote {
  cinema_id: number;
  cinema_name: string;
  group_size: number;
  possible: boolean;
  total_bundles: number | null;
  bundles: BundleCount[];
  message: string;
}

export interface NewMovie {
  title: string;
  release_year: number;
  runtime_minutes: number;
  prerequisite_ids: number[];
  watched: boolean;
}
