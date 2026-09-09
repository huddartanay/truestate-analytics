"""One deterministic boundary; rejected requests never open Stage 13 storage."""
from intelligence.query.models import QueryRequest,Model,RouteDecision,ActionResult,Status,Record,Evidence,Section
from intelligence.query.router import route
from intelligence.query.actions import execute

class QueryResponse(Model):
    request: QueryRequest
    route: RouteDecision
    result: ActionResult

class EvidencePackage(Model):
    """Future answer boundary: rejected/general questions are not forwarded."""
    status: Status
    answer_policy: str
    can_generate: bool
    question: str | None=None
    records: tuple[Record,...]=()
    sections: tuple[Section,...]=()
    evidence: tuple[Evidence,...]=()

def evidence_package(response):
    allowed=response.result.status in (Status.AVAILABLE,Status.PARTIAL)
    return EvidencePackage(status=response.result.status,answer_policy=response.result.answer_policy,
        can_generate=allowed,question=response.request.question if allowed else None,
        records=response.result.records if allowed else (),sections=response.result.sections if allowed else (),
        evidence=response.result.evidence if allowed else ())

def query(request):
    request=QueryRequest.model_validate(request)
    decision=route(request)
    return QueryResponse(request=request,route=decision,result=execute(decision,request.as_of))
