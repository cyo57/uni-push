from pydantic import BaseModel


class DashboardSummary(BaseModel):
    request_count: int
    success_count: int
    failed_count: int
