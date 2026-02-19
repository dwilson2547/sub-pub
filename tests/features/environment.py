"""Behave environment configuration for test fixtures and hooks"""

import os
import sys
import signal
import subprocess
import time
import tempfile
import yaml
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.support.containers import ContainerManager
from tests.support.helpers import KafkaTestHelper, PulsarTestHelper, MessageValidator


def before_all(context):
    """Setup before all tests"""
    # Initialize container manager
    context.container_manager = ContainerManager()
    
    # Initialize helpers storage
    context.helpers = {}
    
    # Initialize message validator
    context.validator = MessageValidator()
    
    # Store test artifacts
    context.temp_dir = tempfile.mkdtemp()
    context.config_files = []
    context.sub_pub_processes = []


def after_all(context):
    """Cleanup after all tests"""
    # Stop all sub-pub processes
    for process in context.sub_pub_processes:
        try:
            process.terminate()
            process.wait(timeout=5)
        except Exception:
            try:
                process.kill()
            except Exception:
                pass
                
    # Close all helpers
    for helper in context.helpers.values():
        try:
            helper.close()
        except Exception:
            pass
            
    # Stop all containers
    context.container_manager.stop_all()
    
    # Cleanup temp files
    import shutil
    try:
        shutil.rmtree(context.temp_dir)
    except Exception:
        pass


def before_scenario(context, scenario):
    """Setup before each scenario"""
    # Reset scenario-specific data
    context.current_config = None
    context.current_process = None
    context.consumed_messages = []
    context.published_messages = []
    
    # Tag-based container startup
    if 'kafka' in scenario.tags:
        if 'kafka' not in context.helpers:
            kafka = context.container_manager.start_kafka()
            context.helpers['kafka'] = KafkaTestHelper(kafka.get_bootstrap_servers())
            context.kafka_container = kafka
            
    if 'pulsar' in scenario.tags:
        if 'pulsar' not in context.helpers:
            pulsar = context.container_manager.start_pulsar()
            context.helpers['pulsar'] = PulsarTestHelper(pulsar.get_service_url())
            context.pulsar_container = pulsar
            
    if 'iggy' in scenario.tags:
        if 'iggy' not in context.helpers:
            iggy = context.container_manager.start_iggy()
            context.iggy_container = iggy
            
    if 'google_pubsub' in scenario.tags:
        if 'google_pubsub' not in context.helpers:
            pubsub = context.container_manager.start_google_pubsub()
            context.google_pubsub_container = pubsub


def after_scenario(context, scenario):
    """Cleanup after each scenario"""
    # Stop sub-pub process for this scenario
    if hasattr(context, 'current_process') and context.current_process:
        try:
            context.current_process.terminate()
            context.current_process.wait(timeout=5)
        except Exception:
            try:
                context.current_process.kill()
            except Exception:
                pass
        context.current_process = None
        
    # Wait a bit for cleanup
    time.sleep(1)


def before_step(context, step):
    """Setup before each step"""
    pass


def after_step(context, step):
    """Cleanup after each step"""
    pass
