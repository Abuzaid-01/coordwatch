"""
Phase 1.3: SQLAlchemy database setup & models for CoordWatch.
Tables:
- accounts(did, handle, alias, created_at, first_seen, enriched)
- posts(id, did, text, text_norm, created_at, topic_id, links, hashtags)
- topics(id, keyword, mode, started_at, last_analyzed_at)
- clusters(id, topic_id, score, raw_score, discount_applied, discount_reason, size, signals_json, reasons_json, example_posts_json, computed_at)
- cluster_members(cluster_id, topic_id, did, node_score)
- topic_analysis_cache(topic_id, graph_json, timeline_json, computed_at)
- evaluation_runs(id, report_json, computed_at)
"""

from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from .config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Account(Base):
    __tablename__ = "accounts"

    did = Column(String, primary_key=True, index=True)
    handle = Column(String, nullable=False, default="")
    alias = Column(String, nullable=False)
    created_at = Column(String, nullable=True)
    first_seen = Column(String, nullable=False)
    enriched = Column(Boolean, default=False)
    enrich_attempts = Column(Integer, default=0)
    enrich_status = Column(String, default="pending")  # pending, ok, failed


class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword = Column(String, unique=True, nullable=False, index=True)
    mode = Column(String, nullable=False, default="hybrid")
    source = Column(String, nullable=False, default="live")  # demo, live, recorded
    started_at = Column(String, nullable=False)
    last_analyzed_at = Column(String, nullable=True)


class Post(Base):
    __tablename__ = "posts"

    id = Column(String, primary_key=True)
    did = Column(String, ForeignKey("accounts.did"), nullable=False, index=True)
    text = Column(Text, nullable=False)
    text_norm = Column(Text, nullable=False)
    created_at = Column(String, nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False, index=True)
    links = Column(Text, nullable=False, default="[]")
    hashtags = Column(Text, nullable=False, default="[]")
    source = Column(String, nullable=False, default="live")  # demo, live, recorded


class Cluster(Base):
    __tablename__ = "clusters"

    id = Column(String, primary_key=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), primary_key=True, index=True)
    score = Column(Integer, nullable=False)
    raw_score = Column(Integer, nullable=False, default=0)
    discount_applied = Column(Float, nullable=False, default=0.0)
    discount_reason = Column(Text, nullable=True)
    size = Column(Integer, nullable=False)
    signals_json = Column(Text, nullable=False, default="{}")
    reasons_json = Column(Text, nullable=False, default="[]")
    example_posts_json = Column(Text, nullable=False, default="[]")
    computed_at = Column(String, nullable=False)


class ClusterMember(Base):
    __tablename__ = "cluster_members"

    cluster_id = Column(String, primary_key=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), primary_key=True, index=True)
    did = Column(String, ForeignKey("accounts.did"), primary_key=True)
    node_score = Column(Integer, nullable=False, default=50)


class TopicAnalysisCache(Base):
    __tablename__ = "topic_analysis_cache"

    topic_id = Column(Integer, ForeignKey("topics.id"), primary_key=True)
    graph_json = Column(Text, nullable=False)
    timeline_json = Column(Text, nullable=False)
    computed_at = Column(String, nullable=False)


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_json = Column(Text, nullable=False)
    computed_at = Column(String, nullable=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
