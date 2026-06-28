import unittest
import base64
import json
import tempfile
from pathlib import Path
from typing import Any

from app.domain.models.tool import ToolRiskLevel, ToolSource
from app.domain.models.tool_result import ToolResult
from app.domain.llm.messages import LLMToolCall
from app.domain.runtime.tool_calling_runtime import ToolCallingRuntime
from app.domain.services.executor import Executor
from app.domain.tools.builtin import create_builtin_tool_registry
from app.domain.tools.registry import ToolRegistry
from app.infrastructure.mcp.adapter import MCPToolAdapter
from app.infrastructure.mcp.config import (
    MCPServerConfig,
    create_playwright_mcp_config,
)
from app.infrastructure.mcp.runtime import MCPRuntime
from app.infrastructure.mcp.browser_observation import (
    BrowserArtifactStore,
    BrowserObservationNormalizer,
)


class FakeMCPClient:
    def __init__(self, *, fail_connect: bool = False) -> None:
        self.fail_connect = fail_connect
        self.connected = False
        self.closed = False
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def connect(self) -> None:
        if self.fail_connect:
            raise RuntimeError("connection refused")
        self.connected = True

    async def close(self) -> None:
        self.connected = False
        self.closed = True

    async def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "browser_navigate",
                "description": "Open a browser page by URL.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                        "wait_ms": {"type": "integer", "default": 0},
                    },
                    "required": ["url"],
                },
            },
            {
                "name": "browser_click",
                "description": "Click an element.",
                "inputSchema": {"type": "object", "properties": {}},
            },
        ]

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        self.calls.append((name, arguments))
        return {
            "content": [{"type": "text", "text": "Example Domain"}],
            "structuredContent": {
                "url": arguments["url"],
                "title": "Example Domain",
            },
            "isError": False,
        }


class FailingCallMCPClient(FakeMCPClient):
    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        raise RuntimeError("connection closed")


def create_adapter(client: FakeMCPClient) -> MCPToolAdapter:
    return MCPToolAdapter(
        client=client,
        config=MCPServerConfig(
            name="playwright",
            tool_name_map={"browser_navigate": "browser.open"},
            tool_risk_levels={"browser.open": ToolRiskLevel.READ_ONLY},
        ),
    )


class MCPToolAdapterTest(unittest.IsolatedAsyncioTestCase):
    async def test_discovery_maps_schema_and_metadata(self) -> None:
        definitions = await create_adapter(FakeMCPClient()).discover_tools()
        definition = definitions[0]

        self.assertEqual(definition.name, "browser.open")
        self.assertEqual(definition.source, ToolSource.MCP)
        self.assertEqual(definition.risk_level, ToolRiskLevel.READ_ONLY)
        self.assertEqual(definition.required, ["url"])
        self.assertEqual(definition.parameters_by_name["url"].type, "string")
        self.assertEqual(definition.parameters_by_name["wait_ms"].default, 0)
        self.assertEqual(definition.metadata["mcp_server"], "playwright")

    async def test_registered_proxy_forwards_and_normalizes(self) -> None:
        client = FakeMCPClient()
        adapter = create_adapter(client)
        registry = ToolRegistry()
        await adapter.register_tools(registry)

        result = await registry.invoke(
            "browser.open",
            {"url": "https://example.com"},
        )

        self.assertTrue(result.success)
        self.assertEqual(result.data["type"], "browser_observation")
        self.assertEqual(
            result.data["observation"]["title"],
            "Example Domain",
        )
        self.assertEqual(
            client.calls,
            [("browser_navigate", {"url": "https://example.com"})],
        )

    async def test_call_failure_returns_structured_error(self) -> None:
        adapter = create_adapter(FailingCallMCPClient())
        await adapter.discover_tools()

        result = await adapter.invoke(
            "browser.open",
            {"url": "https://example.com"},
        )

        self.assertFalse(result.success)
        self.assertEqual(result.data["type"], "browser_observation")
        self.assertEqual(
            result.data["observation"]["error"]["server"],
            "playwright",
        )

    async def test_unclassified_tool_defaults_to_state_changing(self) -> None:
        definitions = await MCPToolAdapter(
            client=FakeMCPClient(),
            config=MCPServerConfig(name="playwright"),
        ).discover_tools()

        self.assertTrue(
            all(
                item.risk_level == ToolRiskLevel.STATE_CHANGING
                for item in definitions
            )
        )


class MCPRuntimeTest(unittest.IsolatedAsyncioTestCase):
    async def test_playwright_config_registers_only_observation_tools(self) -> None:
        client = FakeMCPClient()
        config = create_playwright_mcp_config(enabled=True)
        runtime = MCPRuntime(config, client=client)  # type: ignore[arg-type]
        registry = create_builtin_tool_registry()

        started = await runtime.start(registry)

        self.assertTrue(started)
        self.assertTrue(client.connected)
        self.assertEqual(registry.get_tool("browser.open").definition.source, ToolSource.MCP)
        self.assertIsNone(registry.get_tool("browser_click"))
        self.assertEqual(
            registry.get_tool("browser.extract_links").definition.source,
            ToolSource.BUILTIN,
        )
        await runtime.close()
        self.assertTrue(client.closed)

    async def test_start_failure_keeps_placeholders_and_closes_client(self) -> None:
        client = FakeMCPClient(fail_connect=True)
        runtime = MCPRuntime(
            create_playwright_mcp_config(enabled=True),
            client=client,  # type: ignore[arg-type]
        )
        registry = create_builtin_tool_registry()

        started = await runtime.start(registry)

        self.assertFalse(started)
        self.assertEqual(
            registry.get_tool("browser.open").definition.source,
            ToolSource.BUILTIN,
        )
        self.assertTrue(client.closed)
        self.assertEqual(runtime.last_error, "connection refused")


class BrowserObservationNormalizerTest(unittest.TestCase):
    def test_normalizes_playwright_snapshot_into_stable_observation(self) -> None:
        raw_result = {
            "content": [
                {
                    "type": "text",
                    "text": (
                        "### Page\n"
                        "- Page URL: https://example.com/\n"
                        "- Page Title: Example Domain\n"
                        "- link \"More information\" [ref=e3]\n"
                        "- heading \"Example Domain\" [ref=e1]"
                    ),
                }
            ],
            "structuredContent": {
                "links": [
                    {
                        "text": "More information",
                        "href": "https://www.iana.org/help/example-domains",
                    }
                ]
            },
            "isError": False,
        }

        result = BrowserObservationNormalizer().normalize(
            tool_name="browser.open",
            arguments={"url": "https://example.com"},
            raw_result=raw_result,
        )

        observation = result.data["observation"]
        self.assertTrue(result.success)
        self.assertEqual(observation["url"], "https://example.com/")
        self.assertEqual(observation["title"], "Example Domain")
        self.assertEqual(observation["links"][0]["href"], raw_result["structuredContent"]["links"][0]["href"])
        self.assertEqual(observation["elements"][0]["role"], "link")
        self.assertEqual(observation["elements"][0]["selector"], "ref=e3")
        self.assertNotIn("raw", observation)

    def test_screenshot_is_saved_as_artifact_without_base64_in_result(self) -> None:
        image_bytes = b"small-test-png"
        encoded_image = base64.b64encode(image_bytes).decode("ascii")

        with tempfile.TemporaryDirectory() as directory:
            store = BrowserArtifactStore(Path(directory))
            result = BrowserObservationNormalizer(store).normalize(
                tool_name="browser.screenshot",
                arguments={},
                raw_result={
                    "content": [
                        {
                            "type": "image",
                            "data": encoded_image,
                            "mimeType": "image/png",
                        }
                    ],
                    "isError": False,
                },
            )

            screenshot = result.data["observation"]["screenshot"]
            artifact_path = store.resolve(screenshot)
            self.assertIsNotNone(artifact_path)
            self.assertEqual(artifact_path.read_bytes(), image_bytes)
            self.assertNotIn(encoded_image, json.dumps(result.data))

    def test_expands_safe_playwright_snapshot_reference(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_root = Path(directory) / ".playwright-mcp"
            output_root.mkdir()
            snapshot_path = output_root / "page.yml"
            snapshot_path.write_text(
                '- heading "Example Domain" [ref=e1]\n'
                '- link "More information" [ref=e3]\n',
                encoding="utf-8",
            )
            original_cwd = Path.cwd()
            try:
                import os

                os.chdir(directory)
                result = BrowserObservationNormalizer(
                    playwright_output_root=output_root,
                ).normalize(
                    tool_name="browser.observe",
                    arguments={},
                    raw_result={
                        "content": [
                            {
                                "type": "text",
                                "text": "[Snapshot](.playwright-mcp/page.yml)",
                            }
                        ]
                    },
                )
            finally:
                os.chdir(original_cwd)

        observation = result.data["observation"]
        self.assertIn("Accessibility Snapshot", observation["text"])
        self.assertEqual(len(observation["elements"]), 2)

    def test_executor_builds_browser_observation_step_result(self) -> None:
        tool_result = ToolResult(
            success=True,
            data={
                "type": "browser_observation",
                "content": "Opened https://example.com. Page title: Example Domain.",
                "summary": "Observed page: Example Domain.",
                "observation": {
                    "url": "https://example.com",
                    "title": "Example Domain",
                },
            },
        )

        step_result = Executor()._build_step_result("browser.open", tool_result)

        self.assertEqual(step_result.type, "browser_observation_result")
        self.assertEqual(step_result.summary, "Observed page: Example Domain.")
        self.assertEqual(
            step_result.data["observation"]["title"],
            "Example Domain",
        )


class ToolExecutionTraceTest(unittest.IsolatedAsyncioTestCase):
    async def test_registry_records_mcp_trace_and_redacts_arguments(self) -> None:
        client = FakeMCPClient()
        adapter = MCPToolAdapter(
            client=client,
            config=MCPServerConfig(
                name="playwright",
                tool_name_map={"browser_navigate": "browser.open"},
                tool_risk_levels={"browser.open": ToolRiskLevel.READ_ONLY},
            ),
        )
        registry = ToolRegistry()
        await adapter.register_tools(registry)

        result = await registry.invoke(
            "browser.open",
            {
                "url": "https://example.com",
                "authorization": "Bearer private",
                "nested": {"token": "private-token"},
            },
        )

        trace = result.metadata["tool_trace"]
        self.assertTrue(trace["trace_id"].startswith("tool-call-"))
        self.assertEqual(trace["source"], "mcp")
        self.assertEqual(trace["mcp_server"], "playwright")
        self.assertEqual(trace["internal_tool_name"], "browser.open")
        self.assertEqual(trace["mcp_tool_name"], "browser_navigate")
        self.assertEqual(trace["arguments"]["authorization"], "[REDACTED]")
        self.assertEqual(trace["arguments"]["nested"]["token"], "[REDACTED]")
        self.assertEqual(trace["result_type"], "browser_observation_result")
        self.assertTrue(trace["success"])
        self.assertGreaterEqual(trace["duration_ms"], 0)

    async def test_runtime_events_share_trace_id_and_sanitize_result(self) -> None:
        client = FakeMCPClient()
        adapter = create_adapter(client)
        registry = ToolRegistry()
        await adapter.register_tools(registry)
        runtime = ToolCallingRuntime(
            llm_provider=object(),  # type: ignore[arg-type]
            tool_registry=registry,
        )

        _, trace_item, events = await runtime._invoke_tool(
            tool_call=LLMToolCall(
                id="call-1",
                name="browser.open",
                arguments={
                    "url": "https://example.com",
                    "password": "private-password",
                },
            ),
            allowed_tool_names=["browser.open"],
        )

        started_trace_id = events[0].data["trace_id"]
        completed_trace = events[1].data["tool_trace"]
        self.assertEqual(started_trace_id, completed_trace["trace_id"])
        self.assertEqual(
            events[0].data["arguments"]["password"],
            "[REDACTED]",
        )
        self.assertEqual(
            trace_item.execution_trace.trace_id,
            started_trace_id,
        )

    async def test_rejected_runtime_call_has_failure_trace(self) -> None:
        registry = ToolRegistry()
        runtime = ToolCallingRuntime(
            llm_provider=object(),  # type: ignore[arg-type]
            tool_registry=registry,
        )

        _, trace_item, events = await runtime._invoke_tool(
            tool_call=LLMToolCall(
                id="call-denied",
                name="browser.click",
                arguments={"token": "private"},
            ),
            allowed_tool_names=["browser.open"],
        )

        trace = events[1].data["tool_trace"]
        self.assertFalse(trace["success"])
        self.assertEqual(trace["result_type"], "tool_error")
        self.assertEqual(trace["arguments"]["token"], "[REDACTED]")
        self.assertEqual(trace_item.execution_trace.trace_id, trace["trace_id"])


if __name__ == "__main__":
    unittest.main()
