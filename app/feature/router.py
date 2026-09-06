from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from app.feature.service import build_greeting
from app.settings import Settings, get_settings

router = APIRouter(prefix="/greetings", tags=["greetings"])

SettingsDep = Annotated[Settings, Depends(get_settings)]


class GreetingRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=50, examples=["world"])


class GreetingResponse(BaseModel):
    message: str
    app_name: str


@router.post("", response_model=GreetingResponse, summary="Create a greeting")
async def create_greeting(payload: GreetingRequest, settings: SettingsDep) -> GreetingResponse:
    message = await build_greeting(payload.name, app_name=settings.app_name)
    return GreetingResponse(message=message, app_name=settings.app_name)
