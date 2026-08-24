"""
Vigilo — Real K8s Cluster Collector
Connects to actual EKS cluster and collects live metrics.
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

try:
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException
    K8S_AVAILABLE = True
except ImportError:
    K8S_AVAILABLE = False


class RealCollector:
    """Collects real metrics from a live Kubernetes cluster."""

    def __init__(self, kubeconfig: str = None, context: str = None):
        if not K8S_AVAILABLE:
            raise ImportError("kubernetes package not installed. Run: pip install kubernetes")

        if kubeconfig:
            config.load_kube_config(config_file=kubeconfig, context=context)
        else:
            try:
                config.load_incluster_config()
            except config.ConfigException:
                config.load_kube_config(context=context)

        self.v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()
        self.custom_api = client.CustomObjectsApi()
        self.autoscaling_v2 = client.AutoscalingV2Api()

    def collect(self, namespace: str = None) -> Dict:
        """Collect all cluster metrics."""
        print("  📡 Connecting to cluster...")

        cluster_info = self._get_cluster_info()
        print(f"  ✅ Connected to: {cluster_info.get('name', 'unknown')}")

        print("  📊 Collecting node metrics...")
        nodes = self._get_nodes()

        print("  📦 Collecting pod metrics...")
        pods_at_risk = self._get_pods_at_risk(namespace)

        print("  🔐 Collecting certificate info...")
        certs = self._get_certificates(namespace)

        print("  📈 Collecting HPA status...")
        hpas = self._get_hpa_status(namespace)

        print("  ⚡ Collecting events...")
        events = self._get_recent_events(namespace)

        print("  🚀 Collecting deployments...")
        deployments = self._get_recent_deployments(namespace)

        print("  📋 Collecting resource quotas...")
        quotas = self._get_resource_quotas(namespace)

        return {
            "cluster_info": cluster_info,
            "nodes": nodes,
            "pods_at_risk": pods_at_risk,
            "certificates": certs,
            "hpa_status": hpas,
            "recent_events": events,
            "recent_deployments": deployments,
            "resource_quotas": quotas,
        }

    def get_inventory(self, namespace: str = None) -> Dict:
        """Get cluster inventory (nodes, pods, deployments by namespace)."""
        nodes = self._get_nodes()
        namespaces_data = self._get_namespace_summary(namespace)
        karpenter = self._get_karpenter_info()
        keda = self._get_keda_info(namespace)

        # Determine cluster name from context
        _, active_context = config.list_kube_config_contexts()
        cluster_name = active_context.get("context", {}).get("cluster", "unknown")

        return {
            "cluster": cluster_name,
            "time": datetime.now(timezone.utc).isoformat(),
            "nodes": {
                "total": len(nodes),
                "ready": len([n for n in nodes if n.get("status") == "Ready"]),
                "not_ready": len([n for n in nodes if n.get("status") != "Ready"]),
                "details": nodes
            },
            "namespaces": namespaces_data,
            "karpenter": karpenter,
            "keda": keda,
        }

    def _get_cluster_info(self) -> Dict:
        _, active_context = config.list_kube_config_contexts()
        cluster_name = active_context.get("context", {}).get("cluster", "unknown")
        version_info = client.VersionApi().get_code()

        return {
            "name": cluster_name,
            "version": f"{version_info.major}.{version_info.minor}",
            "region": "us-east-1",  # Could parse from cluster name
            "collection_time": datetime.now(timezone.utc).isoformat()
        }

    def _get_nodes(self) -> List[Dict]:
        nodes = []
        node_list = self.v1.list_node()

        for node in node_list.items:
            name = node.metadata.name
            labels = node.metadata.labels or {}
            status = "Ready"
            for condition in node.status.conditions or []:
                if condition.type == "Ready":
                    status = "Ready" if condition.status == "True" else "NotReady"

            # Get capacity and allocatable
            capacity = node.status.capacity or {}
            allocatable = node.status.allocatable or {}

            # Count pods on this node
            pods_on_node = self.v1.list_pod_for_all_namespaces(
                field_selector=f"spec.nodeName={name},status.phase=Running"
            )

            instance_type = labels.get("node.kubernetes.io/instance-type",
                                       labels.get("beta.kubernetes.io/instance-type", "unknown"))

            # Calculate age
            creation = node.metadata.creation_timestamp
            age_days = (datetime.now(timezone.utc) - creation).days if creation else 0

            nodes.append({
                "name": name,
                "instance_type": instance_type,
                "status": status,
                "cpu_capacity": capacity.get("cpu", "0"),
                "memory_capacity": capacity.get("memory", "0"),
                "pods_running": len(pods_on_node.items),
                "pods_capacity": int(allocatable.get("pods", "0")),
                "age_days": age_days,
                "labels": {k: v for k, v in labels.items() if "NodeGroupType" in k or "karpenter" in k},
            })

        return nodes

    def _get_pods_at_risk(self, namespace: str = None) -> List[Dict]:
        """Find pods with high resource usage or restart counts."""
        pods_at_risk = []

        if namespace:
            pod_list = self.v1.list_namespaced_pod(namespace)
        else:
            pod_list = self.v1.list_pod_for_all_namespaces()

        for pod in pod_list.items:
            if pod.status.phase != "Running":
                continue

            for container_status in (pod.status.container_statuses or []):
                restart_count = container_status.restart_count or 0

                # Find container spec for resource limits
                container_spec = None
                for c in (pod.spec.containers or []):
                    if c.name == container_status.name:
                        container_spec = c
                        break

                # Flag if restarts > 2 or if we have resource concerns
                if restart_count >= 2:
                    limits = container_spec.resources.limits if container_spec and container_spec.resources else {}
                    requests = container_spec.resources.requests if container_spec and container_spec.resources else {}

                    last_state = container_status.last_state
                    last_reason = "Unknown"
                    if last_state and last_state.terminated:
                        last_reason = last_state.terminated.reason or "Unknown"

                    pods_at_risk.append({
                        "name": pod.metadata.name,
                        "namespace": pod.metadata.namespace,
                        "status": "Running",
                        "restart_count": restart_count,
                        "memory_limit": limits.get("memory", "not set"),
                        "memory_request": requests.get("memory", "not set"),
                        "cpu_limit": limits.get("cpu", "not set"),
                        "cpu_request": requests.get("cpu", "not set"),
                        "last_restart_reason": last_reason,
                        "age_hours": int((datetime.now(timezone.utc) - pod.metadata.creation_timestamp).total_seconds() / 3600)
                    })

        return pods_at_risk[:20]  # Top 20 at-risk pods

    def _get_certificates(self, namespace: str = None) -> List[Dict]:
        """Get TLS certificate expiry info from secrets."""
        certs = []
        try:
            if namespace:
                secrets = self.v1.list_namespaced_secret(namespace)
            else:
                secrets = self.v1.list_secret_for_all_namespaces()

            for secret in secrets.items:
                if secret.type == "kubernetes.io/tls":
                    # We can't easily parse cert expiry without cryptography lib
                    # but we can flag TLS secrets for the AI to consider
                    certs.append({
                        "name": secret.metadata.name,
                        "namespace": secret.metadata.namespace,
                        "type": "kubernetes.io/tls",
                        "created": secret.metadata.creation_timestamp.isoformat() if secret.metadata.creation_timestamp else "unknown",
                    })
        except ApiException:
            pass

        return certs[:10]

    def _get_hpa_status(self, namespace: str = None) -> List[Dict]:
        """Get HPA status."""
        hpas = []
        try:
            if namespace:
                hpa_list = self.autoscaling_v2.list_namespaced_horizontal_pod_autoscaler(namespace)
            else:
                hpa_list = self.autoscaling_v2.list_horizontal_pod_autoscaler_for_all_namespaces()

            for hpa in hpa_list.items:
                hpas.append({
                    "name": hpa.metadata.name,
                    "namespace": hpa.metadata.namespace,
                    "min_replicas": hpa.spec.min_replicas,
                    "max_replicas": hpa.spec.max_replicas,
                    "current_replicas": hpa.status.current_replicas,
                    "desired_replicas": hpa.status.desired_replicas,
                })
        except ApiException:
            pass

        return hpas

    def _get_recent_events(self, namespace: str = None) -> List[Dict]:
        """Get recent warning events."""
        events = []
        try:
            if namespace:
                event_list = self.v1.list_namespaced_event(namespace)
            else:
                event_list = self.v1.list_event_for_all_namespaces()

            # Filter warnings from last 24 hours
            cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            for event in event_list.items:
                if event.type == "Warning":
                    last_seen = event.last_timestamp or event.event_time
                    if last_seen and last_seen > cutoff:
                        events.append({
                            "type": event.type,
                            "reason": event.reason,
                            "message": event.message[:200] if event.message else "",
                            "namespace": event.metadata.namespace,
                            "count": event.count or 1,
                            "last_seen": last_seen.isoformat(),
                        })
        except ApiException:
            pass

        return events[:30]  # Top 30 events

    def _get_recent_deployments(self, namespace: str = None) -> List[Dict]:
        """Get recent deployments."""
        deployments = []
        try:
            if namespace:
                deploy_list = self.apps_v1.list_namespaced_deployment(namespace)
            else:
                deploy_list = self.apps_v1.list_deployment_for_all_namespaces()

            for deploy in deploy_list.items:
                replicas = deploy.status.replicas or 0
                ready = deploy.status.ready_replicas or 0
                deployments.append({
                    "name": deploy.metadata.name,
                    "namespace": deploy.metadata.namespace,
                    "replicas": replicas,
                    "ready_replicas": ready,
                    "image": deploy.spec.template.spec.containers[0].image if deploy.spec.template.spec.containers else "unknown",
                })
        except ApiException:
            pass

        return deployments

    def _get_resource_quotas(self, namespace: str = None) -> List[Dict]:
        """Get resource quotas."""
        quotas = []
        try:
            if namespace:
                quota_list = self.v1.list_namespaced_resource_quota(namespace)
            else:
                quota_list = self.v1.list_resource_quota_for_all_namespaces()

            for quota in quota_list.items:
                hard = quota.status.hard or {}
                used = quota.status.used or {}
                quotas.append({
                    "namespace": quota.metadata.namespace,
                    "cpu_limit": hard.get("limits.cpu", "not set"),
                    "cpu_used": used.get("limits.cpu", "0"),
                    "memory_limit": hard.get("limits.memory", "not set"),
                    "memory_used": used.get("limits.memory", "0"),
                })
        except ApiException:
            pass

        return quotas

    def _get_namespace_summary(self, namespace: str = None) -> Dict:
        """Get per-namespace summary."""
        ns_data = {}

        if namespace:
            namespaces = [namespace]
        else:
            ns_list = self.v1.list_namespace()
            namespaces = [ns.metadata.name for ns in ns_list.items]

        for ns in namespaces:
            try:
                pods = self.v1.list_namespaced_pod(ns)
                deploys = self.apps_v1.list_namespaced_deployment(ns)

                running = len([p for p in pods.items if p.status.phase == "Running"])
                pending = len([p for p in pods.items if p.status.phase == "Pending"])
                failed = len([p for p in pods.items if p.status.phase == "Failed"])

                ns_data[ns] = {
                    "deployments": len(deploys.items),
                    "pods_running": running,
                    "pods_pending": pending,
                    "pods_failed": failed,
                }
            except ApiException:
                continue

        return ns_data

    def _get_karpenter_info(self) -> Dict:
        """Get Karpenter nodepool info."""
        try:
            nodepools = self.custom_api.list_cluster_custom_object(
                group="karpenter.sh",
                version="v1",
                plural="nodepools"
            )
            items = nodepools.get("items", [])
            return {
                "nodepools": len(items),
                "names": [np["metadata"]["name"] for np in items],
            }
        except ApiException:
            return {"nodepools": 0, "names": [], "note": "Karpenter not installed or no access"}

    def _get_keda_info(self, namespace: str = None) -> Dict:
        """Get KEDA ScaledObject info."""
        try:
            if namespace:
                scaled_objects = self.custom_api.list_namespaced_custom_object(
                    group="keda.sh",
                    version="v1alpha1",
                    namespace=namespace,
                    plural="scaledobjects"
                )
            else:
                scaled_objects = self.custom_api.list_cluster_custom_object(
                    group="keda.sh",
                    version="v1alpha1",
                    plural="scaledobjects"
                )

            items = scaled_objects.get("items", [])
            paused = len([s for s in items if s.get("metadata", {}).get("annotations", {}).get("autoscaling.keda.sh/paused-replicas")])

            return {
                "scaled_objects": len(items),
                "active": len(items) - paused,
                "paused": paused,
            }
        except ApiException:
            return {"scaled_objects": 0, "active": 0, "paused": 0, "note": "KEDA not installed or no access"}
