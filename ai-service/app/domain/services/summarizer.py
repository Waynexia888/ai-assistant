from app.domain.models.task import Task


class Summarizer:
    """
    Generates the final task summary from step results.
    This class does not update task status, step status, or plan status.
    The caller is responsible for writing the returned summary back to the task.
    """


    async def summarize(self, task: Task) -> str:
        """
        Generates and returns the final task summary from step results.
        This method only returns a summary string.
        It does not mutate the task or emit events.
        """
        
        if task.plan is None:
            return "Task has no plan."
        
        results: list[str] = []

        for index, step in enumerate(task.plan.steps, start=1):
            if step.result:
                results.append(f"{index}. {step.result}")

        if not results:
            return "No step results were generated."

        return "\n".join(results)
