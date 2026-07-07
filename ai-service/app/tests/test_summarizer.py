import unittest

from app.domain.models.plan import Step
from app.domain.models.step_result import StepResult
from app.domain.services.summarizer import Summarizer


class SummarizerBrowserActionTest(unittest.TestCase):
    def test_formats_browser_action_post_observation_and_screenshot(self) -> None:
        summarizer = Summarizer.__new__(Summarizer)
        step = Step(
            description="点击 Log In 按钮",
            tool_name="browser.click",
            result=StepResult(
                type="browser_action_result",
                content="Observed https://www.algoexpert.io/product.",
                data={
                    "action": "browser.click",
                    "executed": True,
                    "screenshot": "artifact://browser/screenshot-test.png",
                    "observation": {
                        "url": "https://www.algoexpert.io/product",
                        "title": "AlgoExpert | Ace the Coding Interviews",
                        "elements": [{"role": "button"}, {"role": "link"}],
                        "links": [{"text": "Log In"}],
                        "public_summary": "Page title: AlgoExpert | Ace the Coding Interviews",
                    },
                    "post_approval_screenshot": {
                        "screenshot": "artifact://browser/screenshot-test.png",
                        "screenshot_url": "/internal/ai/artifacts/browser/screenshot-test.png",
                    },
                },
            ),
        )

        formatted = summarizer._format_step_result(1, step)

        self.assertIn("Result type: browser_action_result", formatted)
        self.assertIn("Action executed: True", formatted)
        self.assertIn("Post-action page URL: https://www.algoexpert.io/product", formatted)
        self.assertIn("Observed element count after action: 2", formatted)
        self.assertIn("Observed link count after action: 1", formatted)
        self.assertIn("Post-action screenshot: /internal/ai/artifacts/browser/screenshot-test.png", formatted)
        self.assertIn("Post-action page evidence:", formatted)


if __name__ == "__main__":
    unittest.main()
