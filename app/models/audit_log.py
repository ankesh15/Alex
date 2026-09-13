import datetime
from sqlalchemy import Column, String, Text, Integer, DateTime
from app.core.db import Base


class AgentAuditLog(Base):
    __tablename__ = "agent_audit_logs"

    task_id = Column(String(64), primary_key=True, index=True)
    module_name = Column(String(50), index=True)
    status = Column(String(20), default="PENDING")
    input_data = Column(Text, nullable=True)
    output_result = Column(Text, nullable=True)

    # Token Metrics
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
