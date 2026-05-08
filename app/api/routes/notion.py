from fastapi import APIRouter, HTTPException, Query, status

from app.services.notion_schema import NotionSchemaService

router = APIRouter(prefix="/notion", tags=["notion"])


@router.get("/schemas")
def list_notion_schemas() -> list[dict[str, str]]:
    return NotionSchemaService().list_schemas()


@router.get("/schemas/check")
async def check_notion_schema(schema: str = Query(default="all")) -> dict | list[dict]:
    service = NotionSchemaService()
    try:
        if schema == "all":
            return [result.model_dump(mode="json") for result in await service.check_all()]
        return (await service.check(schema)).model_dump(mode="json")
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post("/schemas/bootstrap")
async def bootstrap_notion_schema(schema: str = Query(default="all")) -> dict | list[dict]:
    service = NotionSchemaService()
    try:
        if schema == "all":
            return [result.model_dump(mode="json") for result in await service.bootstrap_all()]
        return (await service.bootstrap(schema)).model_dump(mode="json")
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

