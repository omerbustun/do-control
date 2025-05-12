from sqlalchemy import Column, String, DateTime, Integer, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from console.database import Base


class DBDroplet(Base):
    __tablename__ = "droplets"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    region = Column(String, nullable=False)
    size = Column(String, nullable=False)
    ip_address = Column(String, nullable=False)
    status = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False)
    agent_status = Column(String, nullable=True)
    tags = Column(JSON, nullable=True)


class DBTestConfiguration(Base):
    __tablename__ = "test_configurations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    command = Column(String, nullable=False)
    parameters = Column(JSON, nullable=True)
    target_droplets = Column(JSON, nullable=False)
    duration = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by = Column(String, nullable=False)

    executions = relationship("DBTestExecution", back_populates="configuration")


class DBTestExecution(Base):
    __tablename__ = "test_executions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    config_id = Column(String, ForeignKey("test_configurations.id"), nullable=False)
    status = Column(String, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    results = Column(JSON, nullable=True)

    configuration = relationship("DBTestConfiguration", back_populates="executions")
    droplet_results = relationship("DBExecutionResult", back_populates="execution")


class DBExecutionResult(Base):
    __tablename__ = "execution_results"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    execution_id = Column(String, ForeignKey("test_executions.id"), nullable=False)
    droplet_id = Column(String, ForeignKey("droplets.id"), nullable=False)
    status = Column(String, nullable=False)
    results = Column(JSON, nullable=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)

    execution = relationship("DBTestExecution", back_populates="droplet_results")