"""
Execution Engine

Takes a parsed intent (action graph) and executes each step
in order, handling dependencies, errors, and rollback.
"""
import time
from datetime import datetime, timezone
from typing import Any, Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors import registry
from app.models.database import Execution, ExecutionStep, ExecutionStatus
from app.models.schemas import IntentParsed, StepResult

logger = structlog.get_logger()


class ExecutionEngine:
    """Executes parsed intents step by step"""

    def __init__(self, db: AsyncSession, user_connectors: dict[str, dict] = None):
        self.db = db
        self.user_connectors = user_connectors or {}
        self.step_outputs: dict[int, Any] = {}  # step_number -> output

    async def execute(
        self, execution: Execution, parsed: IntentParsed
    ) -> list[StepResult]:
        """Execute all steps in the action graph"""
        results: list[StepResult] = []
        execution.status = ExecutionStatus.EXECUTING
        await self.db.flush()

        for action_step in sorted(parsed.steps, key=lambda s: s.step):
            # Check dependencies
            for dep in action_step.depends_on:
                dep_result = next((r for r in results if r.step == dep), None)
                if dep_result and dep_result.status == "failed":
                    result = StepResult(
                        step=action_step.step,
                        connector=action_step.connector,
                        action=action_step.action,
                        status="skipped",
                        error=f"Dependency step {dep} failed",
                    )
                    results.append(result)
                    continue

            # Resolve parameters with outputs from previous steps
            resolved_params = self._resolve_params(action_step.parameters)

            # Execute the step
            result = await self._execute_step(execution.id, action_step, resolved_params)
            results.append(result)

            # Store output for dependent steps
            if result.output:
                self.step_outputs[action_step.step] = result.output

            # If step failed, mark execution as failed
            if result.status == "failed":
                execution.status = ExecutionStatus.FAILED
                execution.error = result.error
                break

        if execution.status == ExecutionStatus.EXECUTING:
            execution.status = ExecutionStatus.COMPLETED

        execution.completed_at = datetime.now(timezone.utc)
        await self.db.flush()
        return results

    async def _execute_step(
        self, execution_id: str, action_step: Any, parameters: dict
    ) -> StepResult:
        """Execute a single step"""
        start = time.time()

        # Record step in DB
        db_step = ExecutionStep(
            execution_id=execution_id,
            step_order=action_step.step,
            connector_type=action_step.connector,
            action=action_step.action,
            input_data=parameters,
            status=ExecutionStatus.EXECUTING,
            started_at=datetime.now(timezone.utc),
        )
        self.db.add(db_step)
        await self.db.flush()

        try:
            # Get connector config (user's credentials for this connector type)
            config = self.user_connectors.get(action_step.connector, {})
            connector = registry.get_instance(action_step.connector, config)

            if not connector:
                raise ValueError(f"Connector '{action_step.connector}' not found. Available: {[c['type'] for c in registry.list_all()]}")

            # Execute
            output = await connector.execute(action_step.action, parameters)

            duration_ms = int((time.time() - start) * 1000)

            db_step.output_data = output
            db_step.status = ExecutionStatus.COMPLETED
            db_step.completed_at = datetime.now(timezone.utc)
            await self.db.flush()

            success = output.get("success", True) if isinstance(output, dict) else True

            return StepResult(
                step=action_step.step,
                connector=action_step.connector,
                action=action_step.action,
                status="completed" if success else "failed",
                output=output,
                error=output.get("error") if isinstance(output, dict) else None,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = int((time.time() - start) * 1000)
            logger.error("step_execution_failed", step=action_step.step, error=str(e))

            db_step.status = ExecutionStatus.FAILED
            db_step.error = str(e)
            db_step.completed_at = datetime.now(timezone.utc)
            await self.db.flush()

            return StepResult(
                step=action_step.step,
                connector=action_step.connector,
                action=action_step.action,
                status="failed",
                error=str(e),
                duration_ms=duration_ms,
            )

    def _resolve_params(self, parameters: dict) -> dict:
        """Replace {{step.N.field}} references with actual outputs"""
        resolved = {}
        for key, value in parameters.items():
            if isinstance(value, str) and "{{step." in value:
                resolved[key] = self._resolve_reference(value)
            elif isinstance(value, dict):
                resolved[key] = self._resolve_params(value)
            else:
                resolved[key] = value
        return resolved

    def _resolve_reference(self, value: str) -> Any:
        """Resolve a {{step.N.field}} reference"""
        import re
        pattern = r"\{\{step\.(\d+)\.(\w+)\}\}"
        match = re.search(pattern, value)
        if match:
            step_num = int(match.group(1))
            field = match.group(2)
            output = self.step_outputs.get(step_num, {})
            if isinstance(output, dict):
                return output.get(field, value)
        return value
