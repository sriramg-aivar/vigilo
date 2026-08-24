"""
Vigilo — Report Generator
Generates PDF reports, sends email via SES/SMTP, and posts to Microsoft Teams.
"""

import json
import requests
from datetime import datetime
from typing import List


class ReportGenerator:
    """Generates and sends prediction reports."""

    def generate_pdf(self, predictions: dict, metrics: dict, filepath: str):
        """Generate a PDF report."""
        # Using simple text-based PDF for now
        # Can upgrade to reportlab/weasyprint later
        markdown = self._build_markdown_report(predictions, metrics)

        # Save as markdown (PDF generation can be added with weasyprint)
        md_path = filepath.replace(".pdf", ".md") if filepath.endswith(".pdf") else filepath
        with open(md_path, "w") as f:
            f.write(markdown)

        print(f"  📄 Report saved: {md_path}")
        # TODO: Add weasyprint PDF generation
        # from weasyprint import HTML
        # HTML(string=markdown_to_html(markdown)).write_pdf(filepath)

    def send_email(self, predictions: dict, metrics: dict, recipients: List[str],
                   sender: str = None, ses_region: str = "us-east-1"):
        """Send report via AWS SES."""
        import boto3

        if not sender:
            print("  ⚠️  No SES sender configured. Set --sender or SES_SENDER env var.")
            return

        ses = boto3.client("ses", region_name=ses_region)
        subject = self._build_email_subject(predictions)
        body = self._build_email_body(predictions, metrics)

        try:
            ses.send_email(
                Source=sender,
                Destination={"ToAddresses": recipients},
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {
                        "Html": {"Data": body, "Charset": "UTF-8"}
                    }
                }
            )
        except Exception as e:
            print(f"  ❌ Email failed: {e}")

    def send_teams_alert(self, predictions: dict, webhook_url: str):
        """Send alert to Microsoft Teams via incoming webhook."""
        card = self._build_teams_card(predictions)

        try:
            response = requests.post(
                webhook_url,
                json=card,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            if response.status_code not in [200, 202]:
                print(f"  ❌ Teams webhook failed: {response.status_code} {response.text}")
        except Exception as e:
            print(f"  ❌ Teams webhook error: {e}")

    def _build_email_subject(self, predictions: dict) -> str:
        """Build email subject line."""
        preds = predictions.get("predictions", [])
        critical = len([p for p in preds if p.get("severity") == "CRITICAL"])
        warning = len([p for p in preds if p.get("severity") == "WARNING"])
        score = predictions.get("cluster_score", "N/A")

        if critical > 0:
            return f"🚨 Vigilo — {critical} CRITICAL predictions | Score: {score}/10"
        elif warning > 0:
            return f"⚠️ Vigilo — {warning} warnings | Score: {score}/10"
        else:
            return f"✅ Vigilo — Cluster healthy | Score: {score}/10"

    def _build_email_body(self, predictions: dict, metrics: dict) -> str:
        """Build HTML email body."""
        preds = predictions.get("predictions", [])
        score = predictions.get("cluster_score", "N/A")
        summary = predictions.get("summary", "")
        cluster_name = metrics.get("cluster_info", {}).get("name", "Unknown")
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

        rows = ""
        for p in preds:
            color = "#dc3545" if p.get("severity") == "CRITICAL" else "#ffc107" if p.get("severity") == "WARNING" else "#17a2b8"
            rows += f"""
            <tr>
                <td style="padding:8px;border-bottom:1px solid #eee;">
                    <span style="color:{color};font-weight:bold;">{p.get('severity', 'N/A')}</span>
                </td>
                <td style="padding:8px;border-bottom:1px solid #eee;">{p.get('title', 'N/A')}</td>
                <td style="padding:8px;border-bottom:1px solid #eee;">{p.get('time_to_failure', 'N/A')}</td>
                <td style="padding:8px;border-bottom:1px solid #eee;">{p.get('affected_resource', 'N/A')}</td>
                <td style="padding:8px;border-bottom:1px solid #eee;">{p.get('recommended_action', 'N/A')}</td>
            </tr>"""

        return f"""
        <html>
        <body style="font-family:Arial,sans-serif;max-width:800px;margin:0 auto;padding:20px;">
            <h1 style="color:#333;">🔮 Vigilo — Weekly Report</h1>
            <p style="color:#666;">Cluster: <strong>{cluster_name}</strong> | Generated: {now}</p>
            
            <div style="background:#f8f9fa;padding:15px;border-radius:8px;margin:20px 0;">
                <h2 style="margin:0;">Cluster Score: {score}/10</h2>
                <p style="margin:5px 0 0;color:#666;">{summary}</p>
            </div>

            <h2>Predicted Failures (Next 7 Days)</h2>
            <table style="width:100%;border-collapse:collapse;">
                <thead>
                    <tr style="background:#f1f1f1;">
                        <th style="padding:8px;text-align:left;">Severity</th>
                        <th style="padding:8px;text-align:left;">Issue</th>
                        <th style="padding:8px;text-align:left;">Time to Failure</th>
                        <th style="padding:8px;text-align:left;">Affected</th>
                        <th style="padding:8px;text-align:left;">Action</th>
                    </tr>
                </thead>
                <tbody>
                    {rows if rows else '<tr><td colspan="5" style="padding:8px;text-align:center;">✅ No predicted failures</td></tr>'}
                </tbody>
            </table>

            <hr style="margin:30px 0;border:none;border-top:1px solid #eee;">
            <p style="color:#999;font-size:12px;">
                Powered by Vigilo | AI-driven Kubernetes failure prediction<br>
                Predictions are AI-generated based on cluster metrics and trend analysis.
            </p>
        </body>
        </html>
        """

    def _build_teams_card(self, predictions: dict) -> dict:
        """Build Microsoft Teams Adaptive Card."""
        preds = predictions.get("predictions", [])
        score = predictions.get("cluster_score", "N/A")
        summary = predictions.get("summary", "")

        critical = [p for p in preds if p.get("severity") == "CRITICAL"]
        warning = [p for p in preds if p.get("severity") == "WARNING"]

        # Build facts for top predictions
        facts = []
        for p in (critical + warning)[:5]:  # Top 5 predictions
            icon = "🚨" if p.get("severity") == "CRITICAL" else "⚠️"
            facts.append({
                "name": f"{icon} {p.get('title', 'Unknown')}",
                "value": f"Failure in {p.get('time_to_failure', '?')} | Action: {p.get('recommended_action', 'Check manually')}"
            })

        return {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "body": [
                            {
                                "type": "TextBlock",
                                "text": "🔮 Vigilo",
                                "weight": "Bolder",
                                "size": "Large"
                            },
                            {
                                "type": "TextBlock",
                                "text": f"Cluster Score: {score}/10 | {len(critical)} Critical | {len(warning)} Warnings",
                                "color": "Attention" if critical else "Warning" if warning else "Good"
                            },
                            {
                                "type": "TextBlock",
                                "text": summary,
                                "wrap": True
                            },
                            {
                                "type": "FactSet",
                                "facts": facts
                            }
                        ]
                    }
                }
            ]
        }

    def _build_markdown_report(self, predictions: dict, metrics: dict) -> str:
        """Build markdown report."""
        preds = predictions.get("predictions", [])
        score = predictions.get("cluster_score", "N/A")
        summary = predictions.get("summary", "")
        cluster_name = metrics.get("cluster_info", {}).get("name", "Unknown")
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

        md = f"""# 🔮 Vigilo — Cluster Health Report

**Cluster:** {cluster_name}  
**Generated:** {now}  
**Cluster Score:** {score}/10  

---

## Summary

{summary}

---

## Predicted Failures (Next 7 Days)

| Severity | Issue | Time to Failure | Affected | Action |
|----------|-------|-----------------|----------|--------|
"""
        for p in preds:
            icon = "🚨" if p.get("severity") == "CRITICAL" else "⚠️" if p.get("severity") == "WARNING" else "ℹ️"
            md += f"| {icon} {p.get('severity', 'N/A')} | {p.get('title', 'N/A')} | {p.get('time_to_failure', 'N/A')} | {p.get('affected_resource', 'N/A')} | {p.get('recommended_action', 'N/A')} |\n"

        md += f"""
---

## Detailed Predictions

"""
        for i, p in enumerate(preds, 1):
            md += f"""### {i}. {p.get('title', 'Unknown')}

- **Severity:** {p.get('severity', 'N/A')}
- **Category:** {p.get('category', 'N/A')}
- **Time to failure:** {p.get('time_to_failure', 'N/A')}
- **Affected resource:** {p.get('affected_resource', 'N/A')}
- **Current value:** {p.get('current_value', 'N/A')}
- **Threshold:** {p.get('threshold', 'N/A')}
- **Growth rate:** {p.get('growth_rate', 'N/A')}
- **Confidence:** {p.get('confidence', 'N/A')}
- **Impact if ignored:** {p.get('impact', 'N/A')}
- **Recommended action:** {p.get('recommended_action', 'N/A')}

"""

        md += """---

*Powered by Vigilo — AI-driven Kubernetes failure prediction*
"""
        return md
