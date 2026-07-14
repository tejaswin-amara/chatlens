from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from sqlalchemy.orm import declarative_base
from pgvector.sqlalchemy import Vector

Base = declarative_base()

class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (Index('idx_chat_timestamp', 'chat_name', 'timestamp'),)
    
    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String)
    chat_name = Column(String, index=True)
    sender = Column(String)
    timestamp = Column(String, index=True)
    text = Column(Text)
    reply_to = Column(String, nullable=True)
    forwarded_from = Column(String, nullable=True)
    embedding = Column(Vector(1536), nullable=True)
