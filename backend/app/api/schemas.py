from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class CreateDocumentRequest(BaseModel):
    collection_name: str
    document: Dict[str, Any]


class UpdateDocumentRequest(BaseModel):
    collection_name: str
    filter_query: Dict[str, Any]
    update_spec: Dict[str, Any]


class DeleteDocumentRequest(BaseModel):
    collection_name: str
    filter_query: Dict[str, Any]


class RunAggregationRequest(BaseModel):
    collection_name: str
    pipeline: List[Dict[str, Any]]
    preset_key: Optional[str] = None


class AggregationResponse(BaseModel):
    success: bool
    collection: str
    stage_count: int
    execution_time_ms: float
    result_count: int
    results: List[Dict[str, Any]]
    error: Optional[str] = None


class TransferFundsRequest(BaseModel):
    from_account_id: str = Field(default="ACC-0001", description="Source account ID")
    to_account_id: str = Field(default="ACC-0002", description="Destination account ID")
    amount: float = Field(default=150.0, gt=0, description="Transfer amount in USD")
    simulate_failure: bool = Field(default=False, description="Simulate failure to trigger ACID rollback")


class TransactionResponse(BaseModel):
    success: bool
    status: str
    transaction_id: Optional[str] = None
    from_account_balance_before: float
    from_account_balance_after: float
    to_account_balance_before: float
    to_account_balance_after: float
    audit_events: List[str]


class CompareIndexQueryRequest(BaseModel):
    collection_name: str = "restaurants_mcdonalds"
    query: Dict[str, Any] = {"borough": "Manhattan"}
    indexed_field: str = "borough"


class CreateIndexRequest(BaseModel):
    collection_name: str
    field_name: str
    order: int = 1
    unique: bool = False


class AcademicReportRequest(BaseModel):
    student_name: str = "Candidate Principal Engineer"
    course_code: str = "21CSE562T"
    assessment: str = "CLA-2: Advanced MongoDB & Polyglot Database Systems"
    include_benchmarks: bool = True
    include_transactions: bool = True
    include_aggregations: bool = True


class AcademicReportResponse(BaseModel):
    course_code: str
    assessment: str
    generated_at: str
    markdown_content: str
    summary: Dict[str, Any]
