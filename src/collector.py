"""
Vigilo — Metrics Collector
Collects cluster metrics from Kubernetes API.
Currently uses mock data. Will be replaced with real K8s client when cluster access is ready.
"""

from datetime import datetime, timedelta
import random


class MetricsCollector:
    """Collects metrics from Kubernetes cluster."""

    def __init__(self, kubeconfig: str = None, context: str = None):
        """
        Initialize collector.
        
        Args:
            kubeconfig: Path to kubeconfig file (None = default ~/.kube/config)
            context: K8s context to use (None = current context)
        """
        self.kubeconfig = kubeconfig
        self.context = context
        # Will initialize kubernetes client when ready
        # from kubernetes import client, config
        # config.load_kube_config(config_file=kubeconfig, context=context)
        # self.v1 = client.CoreV1Api()
        # self.apps_v1 = client.AppsV1Api()

    def collect(self) -> dict:
        """
        Collect all cluster metrics.
        Returns structured metrics dict for the prediction engine.
        """
        # TODO: Replace with real K8s API calls when cluster access granted
        return self._collect_mock_data()

    def _collect_mock_data(self) -> dict:
        """Generate realistic mock cluster data for testing the prediction engine."""
        now = datetime.utcnow()
        
        return {
            "cluster_info": {
                "name": "aivar-production-eks",
                "version": "1.29",
                "region": "us-east-1",
                "node_count": 5,
                "collection_time": now.isoformat()
            },
            "nodes": [
                {
                    "name": "ip-10-0-1-42.ec2.internal",
                    "instance_type": "m5.xlarge",
                    "status": "Ready",
                    "cpu_capacity": "4000m",
                    "cpu_used": "3200m",
                    "cpu_percent": 80,
                    "memory_capacity": "16Gi",
                    "memory_used": "13.5Gi",
                    "memory_percent": 84,
                    "disk_capacity": "100Gi",
                    "disk_used": "78Gi",
                    "disk_percent": 78,
                    "disk_growth_per_day": "2.1Gi",
                    "pods_running": 28,
                    "pods_capacity": 58,
                    "age_days": 45,
                    "conditions": ["Ready", "MemoryPressure: False", "DiskPressure: False"]
                },
                {
                    "name": "ip-10-0-2-18.ec2.internal",
                    "instance_type": "m5.xlarge",
                    "status": "Ready",
                    "cpu_capacity": "4000m",
                    "cpu_used": "2100m",
                    "cpu_percent": 52,
                    "memory_capacity": "16Gi",
                    "memory_used": "10.2Gi",
                    "memory_percent": 64,
                    "disk_capacity": "100Gi",
                    "disk_used": "45Gi",
                    "disk_percent": 45,
                    "disk_growth_per_day": "0.5Gi",
                    "pods_running": 22,
                    "pods_capacity": 58,
                    "age_days": 45,
                    "conditions": ["Ready", "MemoryPressure: False", "DiskPressure: False"]
                },
                {
                    "name": "ip-10-0-3-91.ec2.internal",
                    "instance_type": "m5.large",
                    "status": "Ready",
                    "cpu_capacity": "2000m",
                    "cpu_used": "1800m",
                    "cpu_percent": 90,
                    "memory_capacity": "8Gi",
                    "memory_used": "7.2Gi",
                    "memory_percent": 90,
                    "disk_capacity": "50Gi",
                    "disk_used": "42Gi",
                    "disk_percent": 84,
                    "disk_growth_per_day": "1.8Gi",
                    "pods_running": 15,
                    "pods_capacity": 29,
                    "age_days": 90,
                    "conditions": ["Ready", "MemoryPressure: False", "DiskPressure: False"]
                }
            ],
            "pods_at_risk": [
                {
                    "name": "payment-processor-7d4f8b6c9-x2k4m",
                    "namespace": "production",
                    "status": "Running",
                    "restart_count": 3,
                    "restart_trend": "increasing (0→1→2→3 over 7 days)",
                    "memory_request": "512Mi",
                    "memory_limit": "768Mi",
                    "memory_current": "680Mi",
                    "memory_percent_of_limit": 88,
                    "memory_growth_per_hour": "5Mi",
                    "cpu_request": "250m",
                    "cpu_limit": "500m",
                    "cpu_current": "380m",
                    "last_restart_reason": "OOMKilled",
                    "age_hours": 168
                },
                {
                    "name": "redis-cache-0",
                    "namespace": "production",
                    "status": "Running",
                    "restart_count": 0,
                    "memory_request": "1Gi",
                    "memory_limit": "2Gi",
                    "memory_current": "1.7Gi",
                    "memory_percent_of_limit": 85,
                    "memory_growth_per_hour": "8Mi",
                    "cpu_request": "500m",
                    "cpu_limit": "1000m",
                    "cpu_current": "450m",
                    "age_hours": 720
                },
                {
                    "name": "log-aggregator-5f9d8c7b2-p8n3v",
                    "namespace": "monitoring",
                    "status": "Running",
                    "restart_count": 1,
                    "memory_request": "256Mi",
                    "memory_limit": "512Mi",
                    "memory_current": "490Mi",
                    "memory_percent_of_limit": 96,
                    "memory_growth_per_hour": "3Mi",
                    "cpu_request": "100m",
                    "cpu_limit": "200m",
                    "cpu_current": "185m",
                    "age_hours": 48
                }
            ],
            "certificates": [
                {
                    "name": "ingress-tls-production",
                    "namespace": "production",
                    "issuer": "letsencrypt-prod",
                    "expires_at": (now + timedelta(days=8)).isoformat(),
                    "days_until_expiry": 8,
                    "auto_renew": True,
                    "last_renewal_status": "success"
                },
                {
                    "name": "api-gateway-tls",
                    "namespace": "gateway",
                    "issuer": "internal-ca",
                    "expires_at": (now + timedelta(days=3)).isoformat(),
                    "days_until_expiry": 3,
                    "auto_renew": False,
                    "last_renewal_status": "n/a"
                }
            ],
            "hpa_status": [
                {
                    "name": "payment-processor",
                    "namespace": "production",
                    "min_replicas": 2,
                    "max_replicas": 5,
                    "current_replicas": 4,
                    "desired_replicas": 5,
                    "cpu_target": 70,
                    "cpu_current": 82,
                    "status": "near_max — 4/5 replicas, CPU at 82% (target 70%)"
                }
            ],
            "recent_events": [
                {
                    "type": "Warning",
                    "reason": "FailedScheduling",
                    "message": "0/3 nodes available: 2 Insufficient memory, 1 Insufficient cpu",
                    "namespace": "production",
                    "count": 5,
                    "first_seen": (now - timedelta(hours=6)).isoformat(),
                    "last_seen": (now - timedelta(hours=1)).isoformat()
                },
                {
                    "type": "Warning",
                    "reason": "OOMKilled",
                    "message": "Container payment-processor exceeded memory limit",
                    "namespace": "production",
                    "count": 3,
                    "first_seen": (now - timedelta(days=7)).isoformat(),
                    "last_seen": (now - timedelta(hours=12)).isoformat()
                },
                {
                    "type": "Normal",
                    "reason": "ScalingReplicaSet",
                    "message": "Scaled up payment-processor from 3 to 4 replicas",
                    "namespace": "production",
                    "count": 1,
                    "first_seen": (now - timedelta(hours=2)).isoformat()
                }
            ],
            "resource_quotas": [
                {
                    "namespace": "production",
                    "cpu_limit": "12000m",
                    "cpu_used": "8500m",
                    "cpu_percent": 71,
                    "memory_limit": "32Gi",
                    "memory_used": "27Gi",
                    "memory_percent": 84
                }
            ],
            "recent_deployments": [
                {
                    "name": "payment-processor",
                    "namespace": "production",
                    "image": "aivar/payment-processor:v2.4.1",
                    "deployed_at": (now - timedelta(hours=12)).isoformat(),
                    "replicas": 4,
                    "status": "running",
                    "resource_change": "memory_limit increased from 512Mi to 768Mi"
                }
            ]
        }

    def collect_real(self) -> dict:
        """
        Collect real metrics from K8s cluster.
        TODO: Implement when cluster access is granted.
        """
        raise NotImplementedError("Real cluster collection not yet enabled. Use collect() for mock data.")
