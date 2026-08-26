"""
Vigilo — CLI Interface
"""

import argparse
import json
import sys
from datetime import datetime

from src.predictor import VigiloEngine
from src.collector import MetricsCollector
from src.reporter import ReportGenerator
from src.real_collector import RealCollector


def main():
    parser = argparse.ArgumentParser(
        prog="vigilo",
        description="🔮 Vigilo — Predict Kubernetes failures before they happen"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- scan command ---
    scan_parser = subparsers.add_parser("scan", help="Scan cluster and generate predictions")
    scan_parser.add_argument("--kubeconfig", type=str, default=None, help="Path to kubeconfig file")
    scan_parser.add_argument("--context", type=str, default=None, help="K8s context to use")
    scan_parser.add_argument("--region", type=str, default="us-east-1", help="AWS region for Bedrock")
    scan_parser.add_argument("--model", type=str, default="us.anthropic.claude-sonnet-4-5-20250929-v1:0", help="Bedrock model ID")
    scan_parser.add_argument("--bedrock-key", type=str, default=None, help="AWS Access Key for Bedrock (if different account)")
    scan_parser.add_argument("--bedrock-secret", type=str, default=None, help="AWS Secret Key for Bedrock")
    scan_parser.add_argument("--bedrock-token", type=str, default=None, help="AWS Session Token for Bedrock")
    scan_parser.add_argument("--output", type=str, choices=["terminal", "json", "pdf"], default="terminal", help="Output format")
    scan_parser.add_argument("--output-file", type=str, default=None, help="Output file path (for json/pdf)")
    scan_parser.add_argument("--mock", action="store_true", help="Use mock data instead of real cluster")
    scan_parser.add_argument("--dry-run", action="store_true", help="Test without calling Bedrock (uses sample predictions)")

    # --- predict-deploy command ---
    deploy_parser = subparsers.add_parser("predict-deploy", help="Predict impact of a deployment")
    deploy_parser.add_argument("--manifest", type=str, required=True, help="Path to deployment manifest (YAML/JSON)")
    deploy_parser.add_argument("--kubeconfig", type=str, default=None, help="Path to kubeconfig file")
    deploy_parser.add_argument("--region", type=str, default="us-east-1", help="AWS region for Bedrock")
    deploy_parser.add_argument("--model", type=str, default="us.anthropic.claude-sonnet-4-5-20250929-v1:0", help="Bedrock model ID")
    deploy_parser.add_argument("--mock", action="store_true", help="Use mock cluster data")

    # --- report command ---
    report_parser = subparsers.add_parser("report", help="Generate and send report to Teams")
    report_parser.add_argument("--teams-webhook", type=str, help="Microsoft Teams incoming webhook URL")
    report_parser.add_argument("--region", type=str, default="us-east-1", help="AWS region")
    report_parser.add_argument("--mock", action="store_true", help="Use mock data")

    # --- shutdown command --- REMOVED
    # --- wakeup command --- REMOVED

    # --- status command ---
    status_parser = subparsers.add_parser("status", help="Show cluster inventory (nodes, pods, deployments)")
    status_parser.add_argument("--kubeconfig", type=str, default=None, help="Path to kubeconfig file")
    status_parser.add_argument("--context", type=str, default=None, help="K8s context to use")
    status_parser.add_argument("--namespace", type=str, default=None, help="Target namespace")
    status_parser.add_argument("--output", type=str, choices=["terminal", "json"], default="terminal", help="Output format")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "scan":
        run_scan(args)
    elif args.command == "predict-deploy":
        run_predict_deploy(args)
    elif args.command == "report":
        run_report(args)
    elif args.command == "status":
        run_status(args)


def run_scan(args):
    """Run a cluster scan and generate predictions."""
    print("🔮 Vigilo — Scanning cluster...\n")

    # Collect metrics
    if args.mock:
        collector = MetricsCollector(kubeconfig=args.kubeconfig, context=args.context)
        metrics = collector.collect()
        print("📊 Using mock cluster data (use --kubeconfig for real cluster)\n")
    else:
        try:
            real_collector = RealCollector(kubeconfig=args.kubeconfig, context=args.context)
            metrics = real_collector.collect()
            print("")
        except ImportError as e:
            print(f"❌ {e}")
            print("   Falling back to mock data. Install kubernetes: pip install kubernetes\n")
            collector = MetricsCollector(kubeconfig=args.kubeconfig, context=args.context)
            metrics = collector.collect()
        except Exception as e:
            print(f"❌ Failed to connect to cluster: {e}")
            print("   Falling back to mock data.\n")
            collector = MetricsCollector(kubeconfig=args.kubeconfig, context=args.context)
            metrics = collector.collect()

    # Run predictions
    print("🧠 Analyzing trends with AI...\n")
    if args.dry_run:
        predictions = _sample_predictions()
    else:
        import os
        bedrock_key = args.bedrock_key or os.environ.get("BEDROCK_AWS_ACCESS_KEY_ID")
        bedrock_secret = args.bedrock_secret or os.environ.get("BEDROCK_AWS_SECRET_ACCESS_KEY")
        bedrock_token = args.bedrock_token or os.environ.get("BEDROCK_AWS_SESSION_TOKEN")
        engine = VigiloEngine(
            region=args.region,
            model_id=args.model,
            aws_access_key_id=bedrock_key,
            aws_secret_access_key=bedrock_secret,
            aws_session_token=bedrock_token
        )
        predictions = engine.predict(metrics)

    # Output
    if args.output == "json":
        output = json.dumps(predictions, indent=2)
        if args.output_file:
            with open(args.output_file, "w") as f:
                f.write(output)
            print(f"✅ Predictions saved to {args.output_file}")
        else:
            print(output)
    elif args.output == "pdf":
        reporter = ReportGenerator()
        filepath = args.output_file or f"vigilo-report-{datetime.now().strftime('%Y%m%d-%H%M')}.pdf"
        reporter.generate_pdf(predictions, metrics, filepath)
        print(f"✅ PDF report saved to {filepath}")
    else:
        # Terminal output
        print_predictions(predictions)


def run_predict_deploy(args):
    """Predict deployment impact."""
    print("⚡ Vigilo — Predicting deployment impact...\n")

    # Load deployment manifest
    import yaml
    with open(args.manifest, "r") as f:
        if args.manifest.endswith(".json"):
            deployment_diff = json.load(f)
        else:
            deployment_diff = yaml.safe_load(f)

    # Collect current cluster state
    collector = MetricsCollector(kubeconfig=args.kubeconfig)
    metrics = collector.collect()

    # Predict impact
    print("🧠 Analyzing deployment impact...\n")
    engine = VigiloEngine(region=args.region, model_id=args.model)
    impact = engine.predict_deployment_impact(metrics, deployment_diff)

    # Print results
    print_deployment_impact(impact)


def run_report(args):
    """Generate and send report."""
    print("📧 Vigilo — Generating weekly report...\n")

    if args.mock:
        collector = MetricsCollector()
        metrics = collector.collect()
    else:
        try:
            real_collector = RealCollector()
            metrics = real_collector.collect()
        except Exception:
            collector = MetricsCollector()
            metrics = collector.collect()

    engine = VigiloEngine(region=args.region)
    predictions = engine.predict(metrics)

    reporter = ReportGenerator()

    if args.teams_webhook:
        reporter.send_teams_alert(predictions, args.teams_webhook, metrics)
        print("✅ Report sent to Microsoft Teams")
    else:
        import os
        webhook = os.environ.get("TEAMS_WEBHOOK_URL", "")
        if webhook:
            reporter.send_teams_alert(predictions, webhook, metrics)
            print("✅ Report sent to Microsoft Teams")
        else:
            print("⚠️  No Teams webhook. Use --teams-webhook or set TEAMS_WEBHOOK_URL")
            print_predictions(predictions)


def print_predictions(predictions: dict):
    """Pretty print predictions to terminal."""
    if "error" in predictions:
        print(f"❌ Error: {predictions['error']}")
        return

    score = predictions.get("cluster_score", "N/A")
    summary = predictions.get("summary", "")

    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  📊 Cluster Score: {score}/10")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"\n  {summary}\n")

    preds = predictions.get("predictions", [])
    if not preds:
        print("  ✅ No predicted failures in the next 7 days!")
        return

    # Group by severity
    critical = [p for p in preds if p.get("severity") == "CRITICAL"]
    warning = [p for p in preds if p.get("severity") == "WARNING"]
    info = [p for p in preds if p.get("severity") == "INFO"]

    if critical:
        print(f"  🚨 CRITICAL ({len(critical)})")
        print(f"  {'─' * 40}")
        for p in critical:
            print_single_prediction(p)

    if warning:
        print(f"\n  ⚠️  WARNING ({len(warning)})")
        print(f"  {'─' * 40}")
        for p in warning:
            print_single_prediction(p)

    if info:
        print(f"\n  ℹ️  INFO ({len(info)})")
        print(f"  {'─' * 40}")
        for p in info:
            print_single_prediction(p)

    print(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  Total predictions: {len(preds)} | Critical: {len(critical)} | Warning: {len(warning)} | Info: {len(info)}")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")


def print_single_prediction(p: dict):
    """Print a single prediction."""
    print(f"\n  [{p.get('category', 'UNKNOWN')}] {p.get('title', 'Unknown')}")
    print(f"  ⏱  Time to failure: {p.get('time_to_failure', 'unknown')}")
    print(f"  📍 Affected: {p.get('affected_resource', 'unknown')}")
    print(f"  📈 Current: {p.get('current_value', 'N/A')} → Threshold: {p.get('threshold', 'N/A')}")
    print(f"  🎯 Confidence: {p.get('confidence', 'N/A')}")
    print(f"  💡 Action: {p.get('recommended_action', 'N/A')}")


def print_deployment_impact(impact: dict):
    """Print deployment impact analysis."""
    if "error" in impact:
        print(f"❌ Error: {impact['error']}")
        return

    safe = impact.get("deployment_safe", None)
    risk = impact.get("risk_level", "UNKNOWN")
    summary = impact.get("summary", "")

    icon = "✅" if safe else "🚨"
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  {icon} Deployment {'SAFE' if safe else 'RISKY'} | Risk Level: {risk}")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"\n  {summary}\n")

    delta = impact.get("resource_delta", {})
    if delta:
        print(f"  📊 Resource Impact:")
        print(f"     CPU change: {delta.get('cpu_change', 'N/A')}")
        print(f"     Memory change: {delta.get('memory_change', 'N/A')}")
        print(f"     CPU headroom after: {delta.get('remaining_headroom_cpu', 'N/A')}")
        print(f"     Memory headroom after: {delta.get('remaining_headroom_memory', 'N/A')}")

    impacts = impact.get("impacts", [])
    if impacts:
        print(f"\n  ⚡ Predicted Impacts ({len(impacts)}):")
        for i in impacts:
            sev_icon = "🚨" if i.get("severity") == "CRITICAL" else "⚠️" if i.get("severity") == "WARNING" else "ℹ️"
            print(f"\n  {sev_icon} [{i.get('category')}] {i.get('description')}")
            print(f"     Affected: {', '.join(i.get('affected_resources', []))}")
            print(f"     Action: {i.get('recommendation', 'N/A')}")

    print(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")


if __name__ == "__main__":
    main()


def run_status(args):
    """Show cluster inventory."""
    try:
        real_collector = RealCollector(kubeconfig=args.kubeconfig, context=args.context)
        status = real_collector.get_inventory(namespace=args.namespace)
    except Exception as e:
        print(f"  ⚠️  Cannot connect to cluster: {e}")
        print(f"  Using mock data.\n")
        collector = MetricsCollector()
        status = {
            "cluster": "vigilo-test",
            "nodes": {"total": 2, "ready": 2, "not_ready": 0, "details": []},
            "namespaces": {},
            "karpenter": {"nodepools": 0},
            "keda": {"scaled_objects": 0, "active": 0, "paused": 0}
        }

    if args.output == "json":
        print(json.dumps(status, indent=2, default=str))
    else:
        print_cluster_status(status)


def print_cluster_status(status: dict):
    """Pretty print cluster status."""
    nodes = status.get("nodes", {})
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  📊 Cluster: {status.get('cluster', 'Unknown')}")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    print(f"  🖥  Nodes: {nodes.get('total', 0)} total | {nodes.get('ready', 0)} ready | {nodes.get('not_ready', 0)} not ready")
    print(f"  {'─' * 40}")
    for n in nodes.get("details", []):
        print(f"  • {n['name']} ({n['type']}) — {n['status']} — {n['pods']} pods")

    print(f"\n  📦 Namespaces:")
    print(f"  {'─' * 40}")
    for ns, data in status.get("namespaces", {}).items():
        pods = data.get("pods_running", 0)
        deploys = data.get("deployments", 0)
        print(f"  • {ns}: {deploys} deployments, {pods} pods running")

    karpenter = status.get("karpenter", {})
    print(f"\n  🚀 Karpenter: {karpenter.get('active_nodes', 0)} nodes across {karpenter.get('nodepools', 0)} pools")

    keda = status.get("keda", {})
    print(f"  ⚡ KEDA: {keda.get('active', 0)} active / {keda.get('paused', 0)} paused ScaledObjects")
    print(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")


def _sample_predictions() -> dict:
    """Sample predictions for dry-run testing without Bedrock."""
    return {
        "cluster_score": 5.8,
        "summary": "Cluster has 4 predicted failures within 7 days. Immediate attention needed for disk and memory issues on node ip-10-0-3-91 and log-aggregator pod.",
        "predictions": [
            {
                "id": "pred-001",
                "severity": "CRITICAL",
                "category": "DISK",
                "title": "Node disk will reach capacity",
                "description": "Node ip-10-0-3-91 disk is at 84% and growing 1.8Gi/day. Will reach 95% critical threshold in approximately 4 days.",
                "time_to_failure": "~4 days",
                "current_value": "84% (42Gi/50Gi)",
                "threshold": "95%",
                "growth_rate": "1.8Gi per day",
                "confidence": "HIGH",
                "affected_resource": "ip-10-0-3-91.ec2.internal",
                "recommended_action": "Expand EBS volume from 50Gi to 100Gi or clean unused container images (docker system prune)",
                "impact": "Pod evictions, new pods cannot be scheduled, node becomes NotReady"
            },
            {
                "id": "pred-002",
                "severity": "CRITICAL",
                "category": "MEMORY",
                "title": "Pod OOM kill imminent — log-aggregator",
                "description": "log-aggregator is at 96% memory (490Mi/512Mi) and growing 3Mi/hour. OOM kill expected within 8 hours.",
                "time_to_failure": "~8 hours",
                "current_value": "490Mi / 512Mi limit (96%)",
                "threshold": "512Mi (OOM kill)",
                "growth_rate": "3Mi per hour",
                "confidence": "HIGH",
                "affected_resource": "log-aggregator-5f9d8c7b2-p8n3v (monitoring)",
                "recommended_action": "Increase memory limit to 1Gi. Investigate log volume spike.",
                "impact": "Log aggregation stops, monitoring blind spot, previous restart already occurred"
            },
            {
                "id": "pred-003",
                "severity": "WARNING",
                "category": "CERT",
                "title": "TLS certificate expiring — api-gateway",
                "description": "api-gateway-tls certificate expires in 3 days. Auto-renew is NOT configured.",
                "time_to_failure": "3 days",
                "current_value": "Expires 2026-08-27",
                "threshold": "Expiry date",
                "growth_rate": "N/A",
                "confidence": "HIGH",
                "affected_resource": "api-gateway-tls (gateway namespace)",
                "recommended_action": "Manually renew certificate OR configure cert-manager with auto-renew",
                "impact": "API gateway will serve expired TLS — browsers will block, clients will fail"
            },
            {
                "id": "pred-004",
                "severity": "WARNING",
                "category": "MEMORY",
                "title": "payment-processor approaching OOM (recurring)",
                "description": "payment-processor at 88% memory (680Mi/768Mi), growing 5Mi/hour. Has been OOMKilled 3 times in 7 days with increasing frequency.",
                "time_to_failure": "~18 hours",
                "current_value": "680Mi / 768Mi limit (88%)",
                "threshold": "768Mi (OOM kill)",
                "growth_rate": "5Mi per hour",
                "confidence": "MEDIUM",
                "affected_resource": "payment-processor-7d4f8b6c9-x2k4m (production)",
                "recommended_action": "Increase memory limit to 1.5Gi. Investigate memory leak (3 OOMKills in 7 days suggests a leak).",
                "impact": "Payment processing interrupted, customer transactions fail, restart count increasing"
            },
            {
                "id": "pred-005",
                "severity": "WARNING",
                "category": "SCALING",
                "title": "HPA at scaling limit — payment-processor",
                "description": "HPA is at 4/5 max replicas with CPU at 82% (target 70%). One more traffic spike and scaling is exhausted.",
                "time_to_failure": "Next traffic spike",
                "current_value": "4/5 replicas, 82% CPU",
                "threshold": "5/5 replicas (max)",
                "growth_rate": "CPU trending up",
                "confidence": "MEDIUM",
                "affected_resource": "payment-processor HPA (production)",
                "recommended_action": "Increase HPA maxReplicas to 8 or add nodes to cluster",
                "impact": "Cannot handle traffic spikes, latency increases, requests timeout"
            }
        ]
    }
