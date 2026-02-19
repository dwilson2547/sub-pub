# Kubernetes Deployment Guide

This directory contains the resources needed to deploy sub-pub to Kubernetes using Docker and Helm.

## Prerequisites

- Docker (for building the container image)
- Kubernetes cluster (v1.19+)
- Helm 3 (v3.0+)
- kubectl configured to access your cluster

## Building the Docker Image

Build the Docker image from the repository root:

```bash
docker build -t sub-pub:latest .
```

For production, tag and push to your container registry:

```bash
# Tag for your registry
docker tag sub-pub:latest your-registry.com/sub-pub:latest

# Push to registry
docker push your-registry.com/sub-pub:latest
```

## Deploying with Helm

### Quick Start

Deploy with default values (uses mock adapters for testing):

```bash
helm install sub-pub ./helm/sub-pub
```

### Custom Configuration

Create a custom `values.yaml` file to override defaults:

```yaml
# custom-values.yaml
replicaCount: 2

image:
  repository: your-registry.com/sub-pub
  tag: "0.1.0"
  pullPolicy: Always

config:
  mode: one_to_one
  logLevel: INFO
  
  oneToOne:
    source:
      type: kafka
      connection:
        bootstrapServers: "kafka.default.svc.cluster.local:9092"
        groupId: "sub-pub-group"
    destination:
      type: kafka
      connection:
        bootstrapServers: "kafka-dest.default.svc.cluster.local:9092"
    mappings:
      - source_topic: "orders"
        destination_topic: "orders-processed"
      - source_topic: "payments"
        destination_topic: "payments-processed"

resources:
  limits:
    cpu: 2000m
    memory: 1Gi
  requests:
    cpu: 500m
    memory: 256Mi

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
```

Deploy with custom values:

```bash
helm install sub-pub ./helm/sub-pub -f custom-values.yaml
```

### Configuration Modes

The chart supports all three sub-pub modes:

#### One-to-One Mode

```yaml
config:
  mode: one_to_one
  oneToOne:
    source:
      type: kafka
      connection:
        bootstrapServers: "kafka:9092"
        groupId: "sub-pub-group"
    destination:
      type: kafka
      connection:
        bootstrapServers: "kafka:9092"
    mappings:
      - source_topic: "topic-a"
        destination_topic: "topic-b"
```

#### Funnel Mode

```yaml
config:
  mode: funnel
  funnel:
    sources:
      - type: kafka
        connection:
          bootstrapServers: "kafka:9092"
          groupId: "sub-pub-group"
        topics:
          - "topic-a"
          - "topic-b"
    destination:
      type: kafka
      connection:
        bootstrapServers: "kafka:9092"
    destinationTopic: "aggregated"
```

#### Fan Mode

```yaml
config:
  mode: fan
  fan:
    source:
      type: kafka
      connection:
        bootstrapServers: "kafka:9092"
    sourceTopic: "input"
    destination:
      type: kafka
      connection:
        bootstrapServers: "kafka:9092"
    destinationResolver:
      type: header
      key: destination_topic
```

## Managing the Deployment

### Upgrade

```bash
helm upgrade sub-pub ./helm/sub-pub -f custom-values.yaml
```

### View Status

```bash
helm status sub-pub
kubectl get pods -l app.kubernetes.io/name=sub-pub
```

### View Logs

```bash
kubectl logs -f deployment/sub-pub
```

### Uninstall

```bash
helm uninstall sub-pub
```

## Advanced Configuration

### Autoscaling

Enable HPA (Horizontal Pod Autoscaler):

```yaml
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80
```

### Resource Limits

Adjust resource requests and limits based on your workload:

```yaml
resources:
  limits:
    cpu: 2000m
    memory: 2Gi
  requests:
    cpu: 500m
    memory: 512Mi
```

### Security Context

The deployment runs as a non-root user (UID 1000) by default:

```yaml
podSecurityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 1000

securityContext:
  allowPrivilegeEscalation: false
  capabilities:
    drop:
    - ALL
  readOnlyRootFilesystem: false
```

### Node Affinity

Pin deployments to specific nodes:

```yaml
nodeSelector:
  workload-type: messaging

affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          labelSelector:
            matchExpressions:
              - key: app.kubernetes.io/name
                operator: In
                values:
                  - sub-pub
          topologyKey: kubernetes.io/hostname
```

### Tolerations

Allow scheduling on tainted nodes:

```yaml
tolerations:
  - key: "messaging"
    operator: "Equal"
    value: "true"
    effect: "NoSchedule"
```

## Monitoring

### Future: Metrics Service

When metrics endpoint is implemented, enable the service:

```yaml
service:
  enabled: true
  type: ClusterIP
  port: 8080

serviceMonitor:
  enabled: true
  interval: 30s
```

### Current: Log-based Monitoring

Monitor through application logs:

```bash
kubectl logs -f deployment/sub-pub | grep "metrics"
```

## Troubleshooting

### Pod Not Starting

Check pod events:
```bash
kubectl describe pod <pod-name>
```

Check logs:
```bash
kubectl logs <pod-name>
```

### Configuration Issues

View the ConfigMap:
```bash
kubectl get configmap sub-pub-config -o yaml
```

Edit the ConfigMap:
```bash
kubectl edit configmap sub-pub-config
```

Then restart the deployment:
```bash
kubectl rollout restart deployment/sub-pub
```

### Connection Issues

Verify network connectivity to message brokers:
```bash
kubectl exec -it <pod-name> -- nc -zv kafka 9092
```

## Production Considerations

1. **Image Registry**: Use a private registry for production images
2. **Secrets Management**: Use Kubernetes secrets for sensitive connection details
3. **Network Policies**: Implement network policies to restrict traffic
4. **Resource Quotas**: Set appropriate resource quotas and limits
5. **Monitoring**: Set up comprehensive logging and monitoring
6. **High Availability**: Use multiple replicas and pod disruption budgets
7. **Backup**: Ensure configuration is version-controlled

## Example: Complete Production Deployment

```yaml
# production-values.yaml
replicaCount: 3

image:
  repository: myregistry.com/sub-pub
  tag: "0.1.0"
  pullPolicy: Always

imagePullSecrets:
  - name: registry-credentials

config:
  mode: one_to_one
  logLevel: INFO
  threadPool:
    maxWorkers: 50
    queueSize: 5000
  oneToOne:
    source:
      type: kafka
      connection:
        bootstrapServers: "kafka-cluster.messaging.svc.cluster.local:9092"
        groupId: "sub-pub-prod"
    destination:
      type: kafka
      connection:
        bootstrapServers: "kafka-cluster.messaging.svc.cluster.local:9092"
    mappings:
      - source_topic: "orders"
        destination_topic: "orders-processed"

resources:
  limits:
    cpu: 2000m
    memory: 2Gi
  requests:
    cpu: 1000m
    memory: 1Gi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 20
  targetCPUUtilizationPercentage: 70

affinity:
  podAntiAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchExpressions:
            - key: app.kubernetes.io/name
              operator: In
              values:
                - sub-pub
        topologyKey: kubernetes.io/hostname
```

Deploy:
```bash
helm install sub-pub ./helm/sub-pub \
  -f production-values.yaml \
  --namespace messaging \
  --create-namespace
```
