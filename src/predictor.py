"""
Kubogent Prophecy — Prediction Engine
Feeds cluster metrics to Claude (Bedrock) and generates failure predictions.
"""

import json
import boto3
from datetime import datetime, timedelta


class ProphecyEngine:
    """Core prediction engine using AWS Bedrock (Claude)."""

    def __init__(self, region: str = "us-east-1", model_id: str = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"):
        self.bedrock = boto3.client("bedrock-runtime", region_name=region)
        self.model_id = model_id

    def predict(self, cluster_metrics: dict) -> dict:
        """
        Takes cluster metrics and returns failure predictions.
        
        Args:
            cluster_metrics: Dict containing node, pod, cert, disk, memory, 
                           deployment, and event data from the cluster.
        
        Returns:
            Dict with predictions, risk scores, and recommended actions.
        """
        prompt = self._build_prompt(cluster_metrics)
        response = self._invoke_bedrock(prompt)
        return self._parse_response(response)

    def predict_deployment_impact(self, cluster_metrics: dict, deployment_diff: dict) -> dict:
        """
        Predicts the impact of a deployment before it happens.
        
        Args:
            cluster_metrics: Current cluster state.
            deployment_diff: What's about to change (new resource requests, image, replicas, etc.)
        
        Returns:
            Dict with impact predictions, risks, and conflicts.
        """
        prompt = self._build_deployment_prompt(cluster_metrics, deployment_diff)
        response = self._invoke_bedrock(prompt)
        return self._parse_response(response)

    def _build_prompt(self, metrics: dict) -> str:
        return f"""You are Kubogent Prophecy — an AI engine that predicts Kubernetes cluster failures before they happen.

Analyze the following cluster metrics and predict:
1. What will FAIL in the next 7 days (with confidence level and estimated time)
2. What is at RISK but not yet critical
3. Recommended ACTIONS to prevent each failure

Be specific with predictions. Include:
- Estimated time to failure (hours/days)
- Current value vs threshold
- Growth rate (if applicable)
- Severity: CRITICAL / WARNING / INFO
- Confidence: HIGH / MEDIUM / LOW

Respond in this exact JSON format:
{{
    "cluster_score": <float 0-10>,
    "predictions": [
        {{
            "id": "<unique-id>",
            "severity": "CRITICAL|WARNING|INFO",
            "category": "DISK|MEMORY|CPU|CERT|POD_HEALTH|SCALING|NETWORK",
            "title": "<short title>",
            "description": "<what will happen>",
            "time_to_failure": "<e.g. 72 hours, 5 days>",
            "current_value": "<current metric>",
            "threshold": "<danger threshold>",
            "growth_rate": "<rate of change>",
            "confidence": "HIGH|MEDIUM|LOW",
            "affected_resource": "<node/pod/namespace name>",
            "recommended_action": "<what to do>",
            "impact": "<what happens if ignored>"
        }}
    ],
    "summary": "<1-2 sentence overall cluster health summary>"
}}

=== CLUSTER METRICS (collected at {datetime.utcnow().isoformat()}) ===

{json.dumps(metrics, indent=2)}

=== END METRICS ===

Analyze the trends and predict failures. Only include predictions where you have reasonable confidence based on the data."""

    def _build_deployment_prompt(self, metrics: dict, deployment_diff: dict) -> str:
        return f"""You are Kubogent Prophecy — an AI engine that predicts deployment impact on Kubernetes clusters.

A deployment is about to happen. Analyze:
1. Current cluster state (metrics below)
2. What's about to change (deployment diff below)

Predict:
1. Resource impact (CPU, memory, disk changes)
2. Risk of pod evictions or OOM
3. Conflicts with other workloads (resource quotas, node capacity)
4. Latency or performance impact
5. Scaling implications

Respond in this exact JSON format:
{{
    "deployment_safe": <true|false>,
    "risk_level": "HIGH|MEDIUM|LOW",
    "impacts": [
        {{
            "category": "RESOURCE|EVICTION|CONFLICT|PERFORMANCE|SCALING",
            "description": "<what will happen>",
            "severity": "CRITICAL|WARNING|INFO",
            "affected_resources": ["<pod/node/namespace>"],
            "recommendation": "<what to do>"
        }}
    ],
    "resource_delta": {{
        "cpu_change": "<e.g. +500m>",
        "memory_change": "<e.g. +512Mi>",
        "remaining_headroom_cpu": "<after deploy>",
        "remaining_headroom_memory": "<after deploy>"
    }},
    "summary": "<1-2 sentence deployment risk summary>"
}}

=== CURRENT CLUSTER STATE ===
{json.dumps(metrics, indent=2)}

=== DEPLOYMENT DIFF (About to apply) ===
{json.dumps(deployment_diff, indent=2)}

=== END ===

Predict the impact. Be specific about numbers."""

    def _invoke_bedrock(self, prompt: str) -> str:
        """Call Claude via Bedrock."""
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "temperature": 0.2,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        })

        response = self.bedrock.invoke_model(
            modelId=self.model_id,
            body=body,
            contentType="application/json",
            accept="application/json"
        )

        result = json.loads(response["body"].read())
        return result["content"][0]["text"]

    def _parse_response(self, response_text: str) -> dict:
        """Parse Claude's JSON response."""
        # Find JSON block in response
        try:
            # Try direct parse first
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Extract JSON from markdown code block if wrapped
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
                return json.loads(json_str)
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()
                return json.loads(json_str)
            else:
                return {"error": "Failed to parse prediction", "raw": response_text}
