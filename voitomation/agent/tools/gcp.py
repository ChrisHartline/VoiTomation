"""
GCP Tool — resource queries and actions via GCP Python SDK.

Inc 1: basic resource listing and status queries.
Inc 2+: full resource management (create, update, deploy).
"""

from typing import Any


class GCPTool:
    """GCP resource tool for Lily."""

    def definition(self) -> dict:
        return {
            "name": "gcp_query",
            "description": (
                "Query GCP resources: list services, check status, describe resources. "
                "For write operations (deploy, create, delete), use terraform_apply instead."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "resource_type": {
                        "type": "string",
                        "description": "GCP resource type: services|instances|buckets|functions|...",
                    },
                    "project_id": {
                        "type": "string",
                        "description": "GCP project ID (uses config default if omitted)",
                    },
                    "region": {
                        "type": "string",
                        "description": "GCP region (e.g. us-central1)",
                    },
                    "filter": {
                        "type": "string",
                        "description": "Optional filter expression",
                    },
                },
                "required": ["resource_type"],
            },
        }

    def run(self, tool_input: dict[str, Any]) -> tuple[str, bool]:
        """
        Execute a GCP query.
        Inc 1: returns a stub response. Inc 2 integrates the real GCP SDK.
        """
        resource_type = tool_input.get("resource_type", "")
        project_id = tool_input.get("project_id", "my-project")
        region = tool_input.get("region", "us-central1")
        filter_expr = tool_input.get("filter", "")

        # Inc 1 stub — replace with real GCP SDK calls in Inc 2
        stub_response = (
            f"[GCP STUB] Query: {resource_type} in {project_id}/{region}"
            + (f" filter={filter_expr}" if filter_expr else "")
            + "\nResult: (connect GCP SDK in Inc 2)"
        )
        return stub_response, True
