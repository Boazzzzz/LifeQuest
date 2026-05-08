from fastapi import APIRouter, HTTPException, Query, status

from app.models.automation import (
    AutomationDefinition,
    AutomationDefinitionCreate,
    AutomationDefinitionUpdate,
    AutomationRun,
    AutomationRunCreate,
)
from app.services.automation import AutomationConflictError, AutomationNotFoundError, AutomationService
from app.services.notion_sync import NotionSyncService

router = APIRouter(prefix="/automations", tags=["automations"])


@router.post("", response_model=AutomationDefinition, status_code=status.HTTP_201_CREATED)
def create_automation(payload: AutomationDefinitionCreate) -> AutomationDefinition:
    try:
        return AutomationService().create_definition(payload)
    except AutomationConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.get("", response_model=list[AutomationDefinition])
def list_automations() -> list[AutomationDefinition]:
    return AutomationService().list_definitions()


@router.get("/runs/recent", response_model=list[AutomationRun])
def list_recent_automation_runs(limit: int = Query(default=50, ge=1, le=500)) -> list[AutomationRun]:
    return AutomationService().list_recent_runs(limit=limit)


@router.post("/sync-notion")
async def sync_automations_to_notion() -> dict:
    automations = AutomationService().list_definitions()
    return await NotionSyncService().sync_automations(automations)


@router.get("/{automation_ref}", response_model=AutomationDefinition)
def get_automation(automation_ref: str) -> AutomationDefinition:
    try:
        return AutomationService().get_definition(automation_ref)
    except AutomationNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.patch("/{automation_ref}", response_model=AutomationDefinition)
def update_automation(automation_ref: str, payload: AutomationDefinitionUpdate) -> AutomationDefinition:
    try:
        return AutomationService().update_definition(automation_ref, payload)
    except AutomationNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except AutomationConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.post("/{automation_ref}/runs", response_model=AutomationRun, status_code=status.HTTP_201_CREATED)
def create_automation_run(automation_ref: str, payload: AutomationRunCreate) -> AutomationRun:
    try:
        return AutomationService().create_run(automation_ref, payload)
    except AutomationNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/{automation_ref}/runs", response_model=list[AutomationRun])
def list_automation_runs(
    automation_ref: str,
    limit: int = Query(default=50, ge=1, le=500),
) -> list[AutomationRun]:
    try:
        return AutomationService().list_runs(automation_ref, limit=limit)
    except AutomationNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
