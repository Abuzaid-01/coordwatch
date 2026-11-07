"""CoordWatch Configuration Settings."""
from dataclasses import dataclass, field
from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("DATA_DIR", PROJECT_ROOT / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_DB_PATH = DATA_DIR / "coordwatch.db"
DEFAULT_JSONL_PATH = DATA_DIR / "sample_posts.jsonl"
DEFAULT_DEMO_SEED_PATH = DATA_DIR / "demo_seed.jsonl"


@dataclass
class Settings:
    app_name: str = "CoordWatch API — Narrative Coordination Detection Engine"
    version: str = "1.0.0"
    data_dir: Path = DATA_DIR
    database_path: Path = field(default_factory=lambda: Path(os.getenv("COORDWATCH_DB_PATH", str(DEFAULT_DB_PATH))))
    database_url: str = ""
    sample_jsonl_path: Path = Path(os.getenv("SAMPLE_JSONL_PATH", DEFAULT_JSONL_PATH))
    demo_seed_jsonl_path: Path = Path(os.getenv("DEMO_SEED_JSONL_PATH", DEFAULT_DEMO_SEED_PATH))

    # Security & CORS
    cors_origins: str = os.getenv("CORS_ORIGINS", "*")

    # Bluesky Jetstream WebSocket endpoints (Phase 1 & 2)
    jetstream_url: str = os.getenv(
        "JETSTREAM_URL",
        "wss://jetstream2.us-east.bsky.network/subscribe?wantedCollections=app.bsky.feed.post",
    )
    jetstream_fallback_url: str = os.getenv(
        "JETSTREAM_FALLBACK_URL",
        "wss://jetstream1.us-east.bsky.network/subscribe?wantedCollections=app.bsky.feed.post",
    )

    # Account enrichment endpoints (Phase 3)
    plc_directory_url: str = os.getenv("PLC_DIRECTORY_URL", "https://plc.directory")
    bsky_public_api_url: str = os.getenv("BSKY_PUBLIC_API_URL", "https://public.api.bsky.app")
    enrich_concurrency: int = 5
    max_enrich_attempts: int = 3

    # Signal & Graph thresholds (Phase 4 & 5)
    text_similarity_threshold: float = 0.76
    tight_burst_seconds: int = 60
    max_creation_cohort_hours: int = 48
    min_edge_weight: float = 0.18
    min_cluster_size: int = 3
    max_graph_nodes: int = 160

    # Cluster scoring weights: score = 100 * (0.35*text + 0.25*timing + 0.20*age + 0.20*links)
    weight_text: float = 0.35
    weight_timing: float = 0.25
    weight_age: float = 0.20
    weight_links: float = 0.20

    # False-positive discount factors
    fp_discount_established_dispersed: float = 0.48  # -52% discount
    fp_discount_established_only: float = 0.62       # -38% discount

    def __post_init__(self) -> None:
        self.database_path = Path(self.database_path)
        # One file. SQLAlchemy and sqlite3 both open this path.
        self.database_url = f"sqlite:///{self.database_path}"


settings = Settings()
