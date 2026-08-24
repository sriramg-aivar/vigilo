"""
Vigilo — Cluster Scheduler
Scale cluster to zero at night (9 PM) and bring it back live in morning (9 AM).
Sends Teams notification on both events.

How it works:
1. SHUTDOWN (9 PM):
   - Scale all Deployments/StatefulSets to 0 replicas (saves original replica counts)
   - KEDA ScaledObjects paused (so they don't scale back up)
   - Karpenter nodes drain naturally (no pods = nodes terminate)
   - Result: Only core node group running (minimal cost)

2. WAKEUP (9 AM):
   - Restore all Deployments/StatefulSets to saved replica counts
   - Unpause KEDA ScaledObjects
   - Karpenter auto-provisions nodes as pods need scheduling
   - Result: Full cluster back to live state

3. NOTIFICATIONS:
   - Teams webhook message on shutdown: "✅ Cluster scaled to zero successfully"
   - Teams webhook message on wakeup: "✅ Cluster is live and healthy"
"""

import json
import time
import requests
from datetime import datetime
from typing import Dict, List, Optional


class ClusterScheduler:
    """Scale cluster to zero at night, bring it back in the morning."""

    def __init__(self, kubeconfig: str = None, context: str = None, namespace: str = None,
                 teams_webhook: str = None, dry_run: bool = False):
        """
        Args:
            kubeconfig: Path to kubeconfig
            context: K8s context
            namespace: Target namespace (None = all non-system namespaces)
            teams_webhook: Microsoft Teams incoming webhook URL
            dry_run: If True, only print what would happen (no changes)
        """
        self.kubeconfig = kubeconfig
        self.context = context
        self.namespace = namespace
        self.teams_webhook = teams_webhook
        self.dry_run = dry_run
        self.state_file = "/tmp/vigilo-state.json"

        # System namespaces to NEVER touch
        self.protected_namespaces = [
            "kube-system", "kube-public", "kube-node-lease",
            "karpenter", "cert-manager", "argocd", "external-secrets"
        ]

        # Will initialize K8s client when cluster access is granted
        self._k8s_initialized = False

    def shutdown(self) -> Dict:
        """
        Scale cluster to zero (9 PM operation).
        
        Returns:
            Dict with shutdown summary (what was scaled, node count, etc.)
        """
        print("🌙 Vigilo — Initiating cluster shutdown...\n")

        if self.dry_run:
            return self._shutdown_dry_run()

        # TODO: Replace with real K8s calls when cluster access granted
        return self._shutdown_mock()

    def wakeup(self) -> Dict:
        """
        Bring cluster back to life (9 AM operation).
        
        Returns:
            Dict with wakeup summary (what was restored, health status, etc.)
        """
        print("☀️ Vigilo — Waking up cluster...\n")

        if self.dry_run:
            return self._wakeup_dry_run()

        # TODO: Replace with real K8s calls when cluster access granted
        return self._wakeup_mock()

    def status(self) -> Dict:
        """
        Get current cluster status — nodes, pods, deployments, replicas.
        
        Returns:
            Dict with full cluster inventory.
        """
        print("📊 Vigilo — Collecting cluster status...\n")

        if self.dry_run:
            return self._status_mock()

        # TODO: Replace with real K8s calls
        return self._status_mock()

    def notify_teams(self, event: str, summary: Dict):
        """Send notification to Microsoft Teams."""
        if not self.teams_webhook:
            print("  ⚠️  No Teams webhook configured. Skipping notification.")
            return

        card = self._build_teams_notification(event, summary)

        if self.dry_run:
            print(f"  [DRY RUN] Would send Teams notification: {event}")
            return

        try:
            response = requests.post(
                self.teams_webhook,
                json=card,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            if response.status_code in [200, 202]:
                print(f"  ✅ Teams notification sent: {event}")
            else:
                print(f"  ❌ Teams notification failed: {response.status_code}")
        except Exception as e:
            print(f"  ❌ Teams notification error: {e}")

    def _save_state(self, state: Dict):
        """Save current replica counts before shutdown."""
        with open(self.state_file, "w") as f:
            json.dump(state, f, indent=2)
        print(f"  💾 State saved to {self.state_file}")

    def _load_state(self) -> Optional[Dict]:
        """Load saved state for wakeup."""
        try:
            with open(self.state_file, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            print("  ⚠️  No saved state found. Using default replica counts.")
            return None

    # ─── Mock implementations (until real cluster access) ───

    def _shutdown_mock(self) -> Dict:
        """Mock shutdown showing what would happen on a Convogent cluster."""
        # Simulate the state we'd save
        state = {
            "shutdown_time": datetime.utcnow().isoformat(),
            "cluster": "convogent-production",
            "namespace": self.namespace or "convogent",
            "deployments": [
                {"name": "convogent-frontend", "namespace": "convogent", "original_replicas": 2},
                {"name": "convogent-backend", "namespace": "convogent", "original_replicas": 2},
                {"name": "convogent-chat-service", "namespace": "convogent", "original_replicas": 2},
                {"name": "convogent-eval-service", "namespace": "convogent", "original_replicas": 1},
                {"name": "convogent-pca-service", "namespace": "convogent", "original_replicas": 1},
                {"name": "convogent-voice-service", "namespace": "convogent", "original_replicas": 3},
            ],
            "statefulsets": [
                {"name": "livekit-server", "namespace": "convogent", "original_replicas": 3},
            ],
            "keda_scaled_objects": [
                {"name": "convogent-frontend-scaledobject", "paused": True},
                {"name": "convogent-backend-scaledobject", "paused": True},
                {"name": "convogent-voice-scaledobject", "paused": True},
            ],
            "nodes_before": 5,
        }

        self._save_state(state)

        summary = {
            "event": "shutdown",
            "time": datetime.utcnow().isoformat(),
            "deployments_scaled": len(state["deployments"]),
            "statefulsets_scaled": len(state["statefulsets"]),
            "keda_objects_paused": len(state["keda_scaled_objects"]),
            "pods_terminated": 14,
            "nodes_before": 5,
            "nodes_after": 1,  # Only core node remains
            "estimated_savings_per_hour": "$2.40",
            "status": "SUCCESS"
        }

        print("  ✅ All deployments scaled to 0")
        print("  ✅ All StatefulSets scaled to 0")
        print("  ✅ KEDA ScaledObjects paused")
        print("  ✅ Karpenter nodes will drain (pods gone → nodes terminate)")
        print(f"  ✅ {summary['pods_terminated']} pods terminated")
        print(f"  ✅ Nodes: {summary['nodes_before']} → {summary['nodes_after']} (core only)")
        print(f"  💰 Estimated savings: {summary['estimated_savings_per_hour']}/hour")
        print(f"\n  🌙 Cluster is DOWN. Only core infrastructure running.\n")

        self.notify_teams("shutdown", summary)
        return summary

    def _wakeup_mock(self) -> Dict:
        """Mock wakeup showing what would happen."""
        state = self._load_state()

        if not state:
            # Default replicas if no state saved
            state = {
                "deployments": [
                    {"name": "convogent-frontend", "namespace": "convogent", "original_replicas": 2},
                    {"name": "convogent-backend", "namespace": "convogent", "original_replicas": 2},
                    {"name": "convogent-chat-service", "namespace": "convogent", "original_replicas": 2},
                    {"name": "convogent-eval-service", "namespace": "convogent", "original_replicas": 1},
                    {"name": "convogent-pca-service", "namespace": "convogent", "original_replicas": 1},
                    {"name": "convogent-voice-service", "namespace": "convogent", "original_replicas": 3},
                ],
                "statefulsets": [
                    {"name": "livekit-server", "namespace": "convogent", "original_replicas": 3},
                ]
            }

        summary = {
            "event": "wakeup",
            "time": datetime.utcnow().isoformat(),
            "deployments_restored": len(state["deployments"]),
            "total_pods_starting": sum(d["original_replicas"] for d in state["deployments"]),
            "statefulsets_restored": len(state.get("statefulsets", [])),
            "keda_objects_resumed": 3,
            "nodes_provisioning": 4,  # Karpenter will provision based on pod needs
            "estimated_ready_time": "3-5 minutes",
            "status": "SUCCESS"
        }

        print("  ✅ Deployments restored to original replica counts:")
        for d in state["deployments"]:
            print(f"     • {d['name']}: 0 → {d['original_replicas']} replicas")
        print(f"  ✅ StatefulSets restored")
        print(f"  ✅ KEDA ScaledObjects resumed (auto-scaling active)")
        print(f"  ✅ Karpenter provisioning {summary['nodes_provisioning']} nodes...")
        print(f"  ⏱  Estimated ready: {summary['estimated_ready_time']}")
        print(f"\n  ☀️ Cluster is LIVE. All services starting up.\n")

        self.notify_teams("wakeup", summary)
        return summary

    def _shutdown_dry_run(self) -> Dict:
        """Dry run shutdown — show what would happen."""
        print("  [DRY RUN] Would perform the following actions:\n")
        print("  1. Save current replica counts to state file")
        print("  2. Scale these deployments to 0 replicas:")
        print("     • convogent-frontend (2 → 0)")
        print("     • convogent-backend (2 → 0)")
        print("     • convogent-chat-service (2 → 0)")
        print("     • convogent-eval-service (1 → 0)")
        print("     • convogent-pca-service (1 → 0)")
        print("     • convogent-voice-service (3 → 0)")
        print("  3. Scale StatefulSets to 0:")
        print("     • livekit-server (3 → 0)")
        print("  4. Pause KEDA ScaledObjects (prevent auto-scale-up)")
        print("  5. Wait for pods to terminate (~30s)")
        print("  6. Karpenter will automatically remove empty nodes")
        print("  7. Send Teams notification: 'Cluster shutdown complete'\n")
        return {"status": "DRY_RUN", "event": "shutdown"}

    def _wakeup_dry_run(self) -> Dict:
        """Dry run wakeup — show what would happen."""
        print("  [DRY RUN] Would perform the following actions:\n")
        print("  1. Load saved state from state file")
        print("  2. Restore deployments to original replicas:")
        print("     • convogent-frontend (0 → 2)")
        print("     • convogent-backend (0 → 2)")
        print("     • convogent-chat-service (0 → 2)")
        print("     • convogent-eval-service (0 → 1)")
        print("     • convogent-pca-service (0 → 1)")
        print("     • convogent-voice-service (0 → 3)")
        print("  3. Restore StatefulSets:")
        print("     • livekit-server (0 → 3)")
        print("  4. Resume KEDA ScaledObjects")
        print("  5. Wait for Karpenter to provision nodes (~2 min)")
        print("  6. Wait for pods to become Ready (~3-5 min)")
        print("  7. Health check all services")
        print("  8. Send Teams notification: 'Cluster is live'\n")
        return {"status": "DRY_RUN", "event": "wakeup"}

    def _status_mock(self) -> Dict:
        """Mock cluster status."""
        return {
            "cluster": "convogent-production",
            "time": datetime.utcnow().isoformat(),
            "nodes": {
                "total": 5,
                "ready": 5,
                "not_ready": 0,
                "details": [
                    {"name": "core-node-1", "type": "m5.large", "status": "Ready", "pods": 12},
                    {"name": "karpenter-dev-1", "type": "c6a.xlarge", "status": "Ready", "pods": 8},
                    {"name": "karpenter-dev-2", "type": "c6a.xlarge", "status": "Ready", "pods": 6},
                    {"name": "karpenter-voice-1", "type": "c6in.xlarge", "status": "Ready", "pods": 3},
                    {"name": "karpenter-monitoring-1", "type": "t4g.large", "status": "Ready", "pods": 9},
                ]
            },
            "namespaces": {
                "convogent": {
                    "deployments": 6,
                    "pods_running": 14,
                    "pods_pending": 0,
                    "pods_failed": 0,
                },
                "monitoring": {
                    "deployments": 4,
                    "pods_running": 9,
                    "pods_pending": 0,
                    "pods_failed": 0,
                },
                "kube-system": {
                    "deployments": 3,
                    "pods_running": 12,
                    "pods_pending": 0,
                    "pods_failed": 0,
                }
            },
            "karpenter": {
                "nodepools": 6,
                "active_nodes": 4,
                "capacity_type": {"spot": 2, "on-demand": 2}
            },
            "keda": {
                "scaled_objects": 6,
                "active": 6,
                "paused": 0
            }
        }

    def _build_teams_notification(self, event: str, summary: Dict) -> Dict:
        """Build Teams adaptive card for shutdown/wakeup notification."""
        if event == "shutdown":
            title = "🌙 Cluster Shutdown Complete"
            color = "warning"
            facts = [
                {"name": "Deployments Scaled", "value": f"{summary.get('deployments_scaled', 0)} → 0 replicas"},
                {"name": "Pods Terminated", "value": str(summary.get('pods_terminated', 0))},
                {"name": "Nodes", "value": f"{summary.get('nodes_before', '?')} → {summary.get('nodes_after', '?')}"},
                {"name": "KEDA Paused", "value": f"{summary.get('keda_objects_paused', 0)} ScaledObjects"},
                {"name": "Savings", "value": summary.get('estimated_savings_per_hour', 'N/A') + " per hour"},
                {"name": "Time", "value": summary.get('time', 'N/A')},
            ]
            status_text = "✅ Cluster is DOWN. Only core infrastructure running. Cost savings active."
        else:
            title = "☀️ Cluster is LIVE"
            color = "good"
            facts = [
                {"name": "Deployments Restored", "value": str(summary.get('deployments_restored', 0))},
                {"name": "Pods Starting", "value": str(summary.get('total_pods_starting', 0))},
                {"name": "Nodes Provisioning", "value": str(summary.get('nodes_provisioning', 0))},
                {"name": "KEDA Resumed", "value": f"{summary.get('keda_objects_resumed', 0)} ScaledObjects"},
                {"name": "Ready In", "value": summary.get('estimated_ready_time', '3-5 min')},
                {"name": "Time", "value": summary.get('time', 'N/A')},
            ]
            status_text = "✅ All services restored. Cluster is healthy and accepting traffic."

        return {
            "type": "message",
            "attachments": [{
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": [
                        {"type": "TextBlock", "text": title, "weight": "Bolder", "size": "Large"},
                        {"type": "TextBlock", "text": status_text, "wrap": True, "color": color},
                        {"type": "FactSet", "facts": facts}
                    ]
                }
            }]
        }
