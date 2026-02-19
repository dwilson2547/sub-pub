"""Core message data structure"""
from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime


@dataclass
class Message:
    """Represents a message in the pub-sub system"""
    
    payload: bytes
    headers: Dict[str, str]
    topic: str
    key: Optional[str] = None
    partition: Optional[int] = None
    offset: Optional[int] = None
    timestamp: Optional[datetime] = None
    
    def size(self) -> int:
        """Calculate the size of the message in bytes"""
        size = len(self.payload)
        for k, v in self.headers.items():
            size += len(k.encode('utf-8')) + len(v.encode('utf-8'))
        if self.key:
            size += len(self.key.encode('utf-8'))
        return size
    
    def get_header(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a header value by key"""
        return self.headers.get(key, default)
