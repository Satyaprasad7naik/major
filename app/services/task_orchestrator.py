"""
Task Orchestrator
==================
Starts and stops engine/generator workers (e.g. ECS tasks).
When ECS config is set, uses boto3 to RunTask/StopTask.
Otherwise, start accepts task_arn from caller (external system started the task).
"""

from typing import Optional, Tuple
from app.core.config import settings

# Optional boto3 for ECS
try:
    import boto3
    from botocore.exceptions import ClientError
    _BOTO_AVAILABLE = True
except ImportError:
    _BOTO_AVAILABLE = False
    boto3 = None


def _ecs_configured() -> bool:
    has_task_def = (
        settings.ECS_TASK_DEFINITION
        or (settings.ECS_ENGINE_TASK_DEFINITION and settings.ECS_GENERATOR_TASK_DEFINITION)
    )
    return bool(
        _BOTO_AVAILABLE
        and settings.ECS_CLUSTER
        and has_task_def
        and settings.ECS_SUBNETS
    )


def _task_definition(engine: bool) -> str:
    """Task definition to use: single ECS_TASK_DEFINITION or engine/generator specific."""
    if settings.ECS_TASK_DEFINITION:
        return settings.ECS_TASK_DEFINITION
    return (
        settings.ECS_ENGINE_TASK_DEFINITION
        if engine
        else settings.ECS_GENERATOR_TASK_DEFINITION
    )


def _run_task_overrides(engine: bool) -> dict:
    """Container overrides so the same task definition runs engine or generator on command."""
    container_name = getattr(
        settings, "ECS_WORKER_CONTAINER_NAME", None
    ) or "worker-container"
    command = (
        ["python", "-m", "app.workers.engine_worker"]
        if engine
        else ["python", "-m", "app.workers.generator_worker"]
    )
    return {
        "containerOverrides": [
            {
                "name": container_name,
                "command": command,
            }
        ]
    }


def _parse_list(value: Optional[str]) -> list:
    if not value:
        return []
    return [s.strip() for s in value.split(",") if s.strip()]


def start_engine_task() -> Tuple[Optional[str], Optional[str]]:
    """
    Start the engine worker task (e.g. ECS RunTask).
    Returns (task_arn, error_message). task_arn is set on success.
    """
    if not _ecs_configured():
        return None, "ECS not configured; pass task_arn in request body to register an externally started task"
    try:
        client = boto3.client("ecs")
        subnets = _parse_list(settings.ECS_SUBNETS)
        sec_groups = _parse_list(settings.ECS_SECURITY_GROUPS)
        network_config = {
            "awsvpcConfiguration": {
                "subnets": subnets,
                "assignPublicIp": "ENABLED",
            }
        }
        if sec_groups:
            network_config["awsvpcConfiguration"]["securityGroups"] = sec_groups
        run_kw = dict(
            cluster=settings.ECS_CLUSTER,
            taskDefinition=_task_definition(engine=True),
            launchType=settings.ECS_LAUNCH_TYPE,
            networkConfiguration=network_config,
        )
        if settings.ECS_TASK_DEFINITION:
            run_kw["overrides"] = _run_task_overrides(engine=True)
        resp = client.run_task(**run_kw)
        tasks = resp.get("tasks") or []
        failures = resp.get("failures") or []
        if tasks:
            task_arn = tasks[0].get("taskArn")
            return task_arn, None
        if failures:
            reason = failures[0].get("reason", "Unknown")
            return None, f"ECS RunTask failed: {reason}"
        return None, "ECS RunTask returned no task"
    except ClientError as e:
        return None, str(e)
    except Exception as e:
        return None, str(e)


def stop_engine_task(task_arn: str) -> Optional[str]:
    """
    Stop the engine worker task (e.g. ECS StopTask).
    Returns error_message on failure, None on success.
    """
    if not _ecs_configured():
        return "ECS not configured; cannot stop task from API"
    try:
        client = boto3.client("ecs")
        cluster = settings.ECS_CLUSTER
        client.stop_task(cluster=cluster, task=task_arn)
        return None
    except ClientError as e:
        return str(e)
    except Exception as e:
        return str(e)


def start_generator_task() -> Tuple[Optional[str], Optional[str]]:
    """
    Start the generator worker task (e.g. ECS RunTask).
    Returns (task_arn, error_message). task_arn is set on success.
    """
    if not _ecs_configured():
        return None, "ECS not configured; pass task_arn in request body to register an externally started task"
    try:
        client = boto3.client("ecs")
        subnets = _parse_list(settings.ECS_SUBNETS)
        sec_groups = _parse_list(settings.ECS_SECURITY_GROUPS)
        network_config = {
            "awsvpcConfiguration": {
                "subnets": subnets,
                "assignPublicIp": "ENABLED",
            }
        }
        if sec_groups:
            network_config["awsvpcConfiguration"]["securityGroups"] = sec_groups
        run_kw = dict(
            cluster=settings.ECS_CLUSTER,
            taskDefinition=_task_definition(engine=False),
            launchType=settings.ECS_LAUNCH_TYPE,
            networkConfiguration=network_config,
        )
        if settings.ECS_TASK_DEFINITION:
            run_kw["overrides"] = _run_task_overrides(engine=False)
        resp = client.run_task(**run_kw)
        tasks = resp.get("tasks") or []
        failures = resp.get("failures") or []
        if tasks:
            task_arn = tasks[0].get("taskArn")
            return task_arn, None
        if failures:
            reason = failures[0].get("reason", "Unknown")
            return None, f"ECS RunTask failed: {reason}"
        return None, "ECS RunTask returned no task"
    except ClientError as e:
        return None, str(e)
    except Exception as e:
        return None, str(e)


def stop_generator_task(task_arn: str) -> Optional[str]:
    """
    Stop the generator worker task (e.g. ECS StopTask).
    Returns error_message on failure, None on success.
    """
    if not _ecs_configured():
        return "ECS not configured; cannot stop task from API"
    try:
        client = boto3.client("ecs")
        client.stop_task(cluster=settings.ECS_CLUSTER, task=task_arn)
        return None
    except ClientError as e:
        return str(e)
    except Exception as e:
        return str(e)
