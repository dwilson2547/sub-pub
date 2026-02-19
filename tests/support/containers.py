"""Testcontainer wrappers for message systems

This module provides testcontainer implementations for:
- Kafka
- Pulsar
- Iggy
- Google Pub/Sub Emulator
"""

import json
import time
from typing import Dict, Optional, Any
from testcontainers.kafka import KafkaContainer as TCKafkaContainer
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs


class KafkaContainer:
    """Kafka testcontainer wrapper using testcontainers built-in support"""
    
    def __init__(self, version: str = "7.6.0"):
        """Initialize Kafka container
        
        Args:
            version: Confluent Platform version
        """
        self.version = version
        self.container = None
        self.bootstrap_servers = None
        
    def start(self) -> 'KafkaContainer':
        """Start Kafka container"""
        # Use testcontainers' built-in Kafka support with KRaft
        self.container = TCKafkaContainer(image=f"confluentinc/cp-kafka:{self.version}")
        self.container.with_kraft()  # Use KRaft mode (no ZooKeeper needed)
        self.container.start()
        
        # Get bootstrap servers
        self.bootstrap_servers = self.container.get_bootstrap_server()
        
        # Additional wait for full readiness
        time.sleep(3)
        
        return self
        
    def stop(self):
        """Stop Kafka container"""
        if self.container:
            self.container.stop()
            
    def get_bootstrap_servers(self) -> str:
        """Get Kafka bootstrap servers connection string"""
        return self.bootstrap_servers
        
    def __enter__(self):
        return self.start()
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


class PulsarContainer:
    """Pulsar testcontainer wrapper"""
    
    def __init__(self, version: str = "3.0.0"):
        """Initialize Pulsar container
        
        Args:
            version: Apache Pulsar version
        """
        self.version = version
        self.container = None
        self.service_url = None
        
    def start(self) -> 'PulsarContainer':
        """Start Pulsar container"""
        self.container = DockerContainer(f"apachepulsar/pulsar:{self.version}")
        
        # Start in standalone mode
        self.container.with_command("bin/pulsar standalone")
        
        # Expose ports
        self.container.with_exposed_ports(6650, 8080)
        
        # Start container
        self.container.start()
        
        # Get mapped ports
        port = self.container.get_exposed_port(6650)
        host = self.container.get_container_host_ip()
        self.service_url = f"pulsar://{host}:{port}"
        
        # Wait for Pulsar to be ready
        wait_for_logs(self.container, ".*messaging service is ready.*", timeout=120)
        time.sleep(5)  # Additional wait
        
        return self
        
    def stop(self):
        """Stop Pulsar container"""
        if self.container:
            self.container.stop()
            
    def get_service_url(self) -> str:
        """Get Pulsar service URL"""
        return self.service_url
        
    def __enter__(self):
        return self.start()
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


class IggyContainer:
    """Iggy testcontainer wrapper"""
    
    def __init__(self, version: str = "latest"):
        """Initialize Iggy container
        
        Args:
            version: Iggy version
        """
        self.version = version
        self.container = None
        self.connection_string = None
        
    def start(self) -> 'IggyContainer':
        """Start Iggy container"""
        # Use official Iggy Docker image
        self.container = DockerContainer(f"iggyrs/iggy:{self.version}")
        
        # Expose ports (default Iggy ports)
        self.container.with_exposed_ports(8090, 3000)
        
        # Start container
        self.container.start()
        
        # Get mapped ports
        tcp_port = self.container.get_exposed_port(8090)
        http_port = self.container.get_exposed_port(3000)
        host = self.container.get_container_host_ip()
        
        self.connection_string = f"{host}:{tcp_port}"
        self.http_url = f"http://{host}:{http_port}"
        
        # Wait for Iggy to be ready
        wait_for_logs(self.container, ".*Server is listening.*", timeout=60)
        time.sleep(3)
        
        return self
        
    def stop(self):
        """Stop Iggy container"""
        if self.container:
            self.container.stop()
            
    def get_connection_string(self) -> str:
        """Get Iggy connection string"""
        return self.connection_string
        
    def get_http_url(self) -> str:
        """Get Iggy HTTP API URL"""
        return self.http_url
        
    def __enter__(self):
        return self.start()
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


class GooglePubSubEmulatorContainer:
    """Google Cloud Pub/Sub Emulator testcontainer wrapper"""
    
    def __init__(self, version: str = "latest"):
        """Initialize Google Pub/Sub Emulator container
        
        Args:
            version: gcloud emulator version
        """
        self.version = version
        self.container = None
        self.endpoint = None
        
    def start(self) -> 'GooglePubSubEmulatorContainer':
        """Start Google Pub/Sub Emulator container"""
        # Use official Google Cloud SDK image with Pub/Sub emulator
        self.container = DockerContainer(f"gcr.io/google.com/cloudsdktool/cloud-sdk:{self.version}")
        
        # Start Pub/Sub emulator
        self.container.with_command(
            "gcloud beta emulators pubsub start --host-port=0.0.0.0:8085"
        )
        
        # Expose port
        self.container.with_exposed_ports(8085)
        
        # Start container
        self.container.start()
        
        # Get mapped port
        port = self.container.get_exposed_port(8085)
        host = self.container.get_container_host_ip()
        self.endpoint = f"{host}:{port}"
        
        # Wait for emulator to be ready
        wait_for_logs(self.container, ".*Server started.*", timeout=60)
        time.sleep(3)
        
        return self
        
    def stop(self):
        """Stop Google Pub/Sub Emulator container"""
        if self.container:
            self.container.stop()
            
    def get_endpoint(self) -> str:
        """Get emulator endpoint"""
        return self.endpoint
        
    def __enter__(self):
        return self.start()
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


class ContainerManager:
    """Manager for all testcontainers"""
    
    def __init__(self):
        """Initialize container manager"""
        self.containers: Dict[str, Any] = {}
        
    def start_kafka(self, name: str = "kafka") -> KafkaContainer:
        """Start a Kafka container
        
        Args:
            name: Container instance name
            
        Returns:
            Started KafkaContainer
        """
        container = KafkaContainer()
        container.start()
        self.containers[name] = container
        return container
        
    def start_pulsar(self, name: str = "pulsar") -> PulsarContainer:
        """Start a Pulsar container
        
        Args:
            name: Container instance name
            
        Returns:
            Started PulsarContainer
        """
        container = PulsarContainer()
        container.start()
        self.containers[name] = container
        return container
        
    def start_iggy(self, name: str = "iggy") -> IggyContainer:
        """Start an Iggy container
        
        Args:
            name: Container instance name
            
        Returns:
            Started IggyContainer
        """
        container = IggyContainer()
        container.start()
        self.containers[name] = container
        return container
        
    def start_google_pubsub(self, name: str = "google_pubsub") -> GooglePubSubEmulatorContainer:
        """Start a Google Pub/Sub Emulator container
        
        Args:
            name: Container instance name
            
        Returns:
            Started GooglePubSubEmulatorContainer
        """
        container = GooglePubSubEmulatorContainer()
        container.start()
        self.containers[name] = container
        return container
        
    def get_container(self, name: str) -> Optional[Any]:
        """Get a container by name
        
        Args:
            name: Container instance name
            
        Returns:
            Container instance or None if not found
        """
        return self.containers.get(name)
        
    def stop_all(self):
        """Stop all running containers"""
        for container in self.containers.values():
            try:
                container.stop()
            except Exception as e:
                print(f"Error stopping container: {e}")
        self.containers.clear()
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_all()
