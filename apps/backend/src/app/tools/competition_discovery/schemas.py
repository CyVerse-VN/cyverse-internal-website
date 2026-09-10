from pydantic import BaseModel


class CompetitionDiscoveryRequest(BaseModel):
    topic: str

