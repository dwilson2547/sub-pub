#!/usr/bin/env python3
"""Quick debugging script to test sub-pub with Kafka container"""

import time
import yaml
import tempfile
import subprocess
import sys
from pathlib import Path
from tests.support.containers import KafkaContainer
from tests.support.helpers import KafkaTestHelper

def main():
    print("="*60)
    print("Sub-Pub Kafka Integration Test")
    print("="*60)
    
    # Start Kafka container
    print("\n1. Starting Kafka container...")
    kafka = KafkaContainer()
    kafka.start()
    bootstrap_servers = kafka.get_bootstrap_servers()
    print(f"✓ Kafka started at: {bootstrap_servers}")
    
    # Create helper
    helper = KafkaTestHelper(bootstrap_servers)
    
    try:
        # Publish test messages
        print("\n2. Publishing test messages...")
        helper.publish_message("test-input", "message-1")
        helper.publish_message("test-input", "message-2")
        print("✓ Published 2 messages to 'test-input'")
        
        # Create config
        print("\n3. Creating sub-pub config...")
        config = {
            'mode': 'one_to_one',
            'thread_pool': {
                'max_workers': 5,
                'queue_size': 100
            },
            'back_pressure': {
                'enabled': True,
                'queue_high_watermark': 0.8,
                'queue_low_watermark': 0.5
            },
            'one_to_one': {
                'source': {
                    'type': 'kafka',
                    'connection': {
                        'bootstrap_servers': [bootstrap_servers],
                        'group_id': 'test-group',
                        'auto_offset_reset': 'earliest'
                    }
                },
                'destination': {
                    'type': 'kafka',
                    'connection': {
                        'bootstrap_servers': [bootstrap_servers]
                    }
                },
                'mappings': [
                    {
                        'source_topic': 'test-input',
                        'destination_topic': 'test-output'
                    }
                ]
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config, f)
            config_path = f.name
        
        print(f"✓ Config written to: {config_path}")
        
        # Start sub-pub
        print("\n4. Starting sub-pub...")
        log_file = tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False)
        process = subprocess.Popen(
            [sys.executable, '-m', 'sub_pub.main', '-c', config_path, '-l', 'INFO'],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True
        )
        log_path = log_file.name
        log_file.close()
        print(f"✓ Sub-pub started (logs: {log_path})")
        
        # Wait for processing
        print("\n5. Waiting for message processing...")
        time.sleep(15)
        
        # Check sub-pub status
        if process.poll() is not None:
            print("⚠️  Sub-pub exited early!")
            with open(log_path, 'r') as f:
                print("\nSub-pub logs:")
                print(f.read())
        else:
            print("✓ Sub-pub still running")
            # Show recent logs
            with open(log_path, 'r') as f:
                logs = f.read()
                print(f"\nRecent logs (last 2000 chars):")
                print(logs[-2000:])
        
        # Try to consume from output
        print("\n6. Consuming from output topic...")
        messages = helper.consume_messages(['test-output'], count=2, timeout=15)
        print(f"✓ Consumed {len(messages)} messages")
        
        for i, msg in enumerate(messages):
            print(f"  Message {i+1}: {msg.get('value')}")
        
        # Stop sub-pub
        process.terminate()
        process.wait(timeout=5)
        
        # Results
        print("\n" + "="*60)
        if len(messages) == 2:
            print("✅ TEST PASSED!")
        else:
            print(f"❌ TEST FAILED: Expected 2 messages, got {len(messages)}")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        helper.close()
        kafka.stop()
        print("\n✓ Cleanup complete")

if __name__ == '__main__':
    main()
