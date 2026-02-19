"""Example custom message processors"""
import json
from sub_pub.domain.processor import MessageProcessor
from sub_pub.core.message import Message


class AddTimestampProcessor(MessageProcessor):
    """Example processor that adds a processing timestamp to message headers"""
    
    def process(self, message: Message) -> Message:
        """Add processing timestamp to headers"""
        from datetime import datetime
        message.headers['processed_at'] = datetime.now().isoformat()
        message.headers['processor'] = 'AddTimestampProcessor'
        return message


class JsonEnrichmentProcessor(MessageProcessor):
    """Example processor that enriches JSON payloads"""
    
    def process(self, message: Message) -> Message:
        """Add enrichment data to JSON payload"""
        try:
            payload = json.loads(message.payload.decode('utf-8'))
            payload['enriched'] = True
            payload['processor_version'] = '1.0'
            message.payload = json.dumps(payload).encode('utf-8')
        except Exception as e:
            # If payload is not JSON, just add to headers
            message.headers['enrichment_error'] = str(e)
        
        return message


class FilteringProcessor(MessageProcessor):
    """Example processor that can filter/modify messages based on conditions"""
    
    def __init__(self, filter_key: str = 'priority', min_priority: int = 5):
        self.filter_key = filter_key
        self.min_priority = min_priority
    
    def process(self, message: Message) -> Message:
        """Filter messages based on priority"""
        try:
            payload = json.loads(message.payload.decode('utf-8'))
            priority = payload.get(self.filter_key, 0)
            
            if priority < self.min_priority:
                message.headers['filtered'] = 'true'
                message.headers['reason'] = f'priority {priority} < {self.min_priority}'
            else:
                message.headers['filtered'] = 'false'
        except Exception:
            message.headers['filtered'] = 'false'
            message.headers['reason'] = 'parse_error'
        
        return message
