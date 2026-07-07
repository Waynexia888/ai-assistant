from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.artifacts.service import ArtifactService


router = APIRouter(prefix="/internal/ai/artifacts", tags=["Artifacts"])
artifact_service = ArtifactService()


@router.get("/{source}/{artifact_name}")
async def get_artifact(source: str, artifact_name: str) -> FileResponse:
    artifact = artifact_service.get(source, artifact_name)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found.")

    return FileResponse(
        artifact.path,
        media_type=artifact.media_type,
        headers={
            "Cache-Control": "private, max-age=3600",
            "X-Artifact-Name": artifact.name,
            "X-Artifact-Source": artifact.source,
        },
    )
