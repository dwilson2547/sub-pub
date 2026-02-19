# Sub-Pub Helm Chart

Helm chart for deploying the sub-pub message processor to Kubernetes.

## Quick Start

```bash
# Install with default values (mock adapter)
helm install sub-pub ./sub-pub

# Install with custom values
helm install sub-pub ./sub-pub -f custom-values.yaml

# Upgrade
helm upgrade sub-pub ./sub-pub -f custom-values.yaml

# Uninstall
helm uninstall sub-pub
```

## Example Deployments

### Production Kafka (One-to-One Mode)
```bash
helm install sub-pub ./sub-pub -f ./sub-pub/values-production-kafka.yaml
```

### Pulsar (Funnel Mode)
```bash
helm install sub-pub ./sub-pub -f ./sub-pub/values-pulsar-funnel.yaml
```

## Chart Values

See [sub-pub/values.yaml](sub-pub/values.yaml) for all available configuration options.

## Full Documentation

For detailed deployment instructions, configuration examples, and troubleshooting, see [KUBERNETES.md](KUBERNETES.md).

## Chart Structure

```
sub-pub/
├── Chart.yaml                      # Chart metadata
├── values.yaml                     # Default values
├── values-production-kafka.yaml    # Example: Production Kafka config
├── values-pulsar-funnel.yaml       # Example: Pulsar funnel config
└── templates/
    ├── _helpers.tpl                # Template helpers
    ├── NOTES.txt                   # Post-install notes
    ├── configmap.yaml              # Application configuration
    ├── deployment.yaml             # Deployment resource
    ├── hpa.yaml                    # Horizontal Pod Autoscaler
    ├── service.yaml                # Service (optional)
    └── serviceaccount.yaml         # Service Account
```

## Requirements

- Kubernetes 1.19+
- Helm 3.0+

## Configuration Modes

The chart supports all three sub-pub operating modes:

1. **one_to_one**: Multiple independent source-to-destination mappings
2. **funnel**: Many sources to one destination
3. **fan**: One source to many destinations (with routing)

Set the mode in your values file:

```yaml
config:
  mode: one_to_one  # or funnel or fan
```
