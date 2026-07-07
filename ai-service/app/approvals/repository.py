from typing import Protocol

from app.approvals.models import ApprovalRequest, ApprovalStatus


class ApprovalRepository(Protocol):
    async def save(self, request: ApprovalRequest) -> ApprovalRequest:
        ...

    async def get_by_id(self, approval_id: str) -> ApprovalRequest | None:
        ...

    async def list_by_status(self, status: ApprovalStatus) -> list[ApprovalRequest]:
        ...


class InMemoryApprovalRepository:
    def __init__(self) -> None:
        self._requests: dict[str, ApprovalRequest] = {}

    async def save(self, request: ApprovalRequest) -> ApprovalRequest:
        self._requests[request.id] = request.model_copy(deep=True)
        return request

    async def get_by_id(self, approval_id: str) -> ApprovalRequest | None:
        request = self._requests.get(approval_id)
        return request.model_copy(deep=True) if request is not None else None

    async def list_by_status(self, status: ApprovalStatus) -> list[ApprovalRequest]:
        requests = [
            request.model_copy(deep=True)
            for request in self._requests.values()
            if request.status == status
        ]
        return sorted(requests, key=lambda request: request.created_at)
