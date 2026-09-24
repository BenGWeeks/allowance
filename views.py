from fastapi import APIRouter, Depends, Request
from lnbits.core.models import User
from lnbits.decorators import check_user_exists
from lnbits.helpers import template_renderer
from starlette.responses import HTMLResponse

allowance_generic_router = APIRouter()


def allowance_renderer():
    return template_renderer(["allowance/templates"])


@allowance_generic_router.get("/", response_class=HTMLResponse)
async def index(request: Request, user: User = Depends(check_user_exists)):
    return allowance_renderer().TemplateResponse(
        request=request,
        name="allowance/index.html",
        context={"user": user.json()},
    )
