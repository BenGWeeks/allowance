from http import HTTPStatus

from fastapi import APIRouter, Depends, Query, Request
from lnbits.core.crud import get_user
from lnbits.core.models import WalletTypeInfo
from lnbits.core.services import create_invoice
from lnbits.decorators import (
    get_key_type,
    require_admin_key,
    require_invoice_key,
)
from lnbits.helpers import urlsafe_short_hash
from lnurl import encode as lnurl_encode
from starlette.exceptions import HTTPException

from .crud import (
    create_allowance,
    delete_allowance,
    get_allowance,
    get_allowances,
    update_allowance,
)
from .models import CreateAllowanceData, Allowance

allowance_api_router = APIRouter()

#######################################
##### ADD YOUR API ENDPOINTS HERE #####
#######################################

## Get all the records belonging to the user

@allowance_api_router.get("/api/v1/allowance", status_code=HTTPStatus.OK)
async def api_allowances(
    all_wallets: bool = Query(False),
    wallet: WalletTypeInfo = Depends(get_key_type),
):
    wallet_ids = [wallet.wallet.id]
    if all_wallets:
        user = await get_user(wallet.wallet.user)
        wallet_ids = user.wallet_ids if user else []
    return [allowance.dict() for allowance in await get_allowances(wallet_ids)]


## Get a single record


@allowance_api_router.get(
    "/api/v1/allowance/{allowance_id}",
    status_code=HTTPStatus.OK,
    dependencies=[Depends(require_invoice_key)],
)
async def api_allowance(allowance_id: str):
    allowance = await get_allowance(allowance_id)
    if not allowance:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Allowance does not exist."
        )
    return allowance.dict()


## update a record


@allowance_api_router.put("/api/v1/allowance/{allowance_id}")
async def api_allowance_update(
    data: CreateAllowanceData,
    allowance_id: str,
    wallet: WalletTypeInfo = Depends(get_key_type),
) -> Allowance:
    if not allowance_id:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Allowance does not exist."
        )
    allowance = await get_allowance(allowance_id)
    assert allowance, "Allowance couldn't be retrieved"

    if wallet.wallet.id != allowance.wallet:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail="Not your Allowance."
        )

    for key, value in data.dict().items():
        setattr(allowance, key, value)

    return await update_allowance(allowance)


## Create a new record


@allowance_api_router.post("/api/v1/allowance", status_code=HTTPStatus.CREATED)
async def api_allowance_create(
    request: Request,
    data: CreateAllowanceData,
    key_type: WalletTypeInfo = Depends(require_admin_key),
) -> Allowance:
    allowance_id = urlsafe_short_hash()
    lnurlpay = lnurl_encode(
        str(request.url_for("allowance.api_lnurl_pay", allowance_id=allowance_id))
    )
    lnurlwithdraw = lnurl_encode(
        str(
            request.url_for(
                "allowance.api_lnurl_withdraw", allowance_id=allowance_id
            )
        )
    )
    data.wallet = data.wallet or key_type.wallet.id
    myext = Allowance(
        id=allowance_id,
        lnurlpay=lnurlpay,
        lnurlwithdraw=lnurlwithdraw,
        **data.dict(),
    )
    return await create_allowance(myext)


## Delete a record


@allowance_api_router.delete("/api/v1/allowance/{allowance_id}")
async def api_allowance_delete(
    allowance_id: str, wallet: WalletTypeInfo = Depends(require_admin_key)
):
    allowance = await get_allowance(allowance_id)

    if not allowance:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Allowance does not exist."
        )

    if allowance.wallet != wallet.wallet.id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail="Not your Allowance."
        )

    await delete_allowance(allowance_id)
    return "", HTTPStatus.NO_CONTENT


# ANY OTHER ENDPOINTS YOU NEED

## This endpoint creates a payment


@allowance_api_router.post(
    "/api/v1/allowance/payment/{allowance_id}", status_code=HTTPStatus.CREATED
)
async def api_allowance_create_invoice(
    allowance_id: str, amount: int = Query(..., ge=1), memo: str = ""
) -> dict:
    allowance = await get_allowance(allowance_id)

    if not allowance:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Allowance does not exist."
        )

    # we create a payment and add some tags,
    # so tasks.py can grab the payment once its paid

    try:
        payment_hash, payment_request = await create_invoice(
            wallet_id=allowance.wallet,
            amount=amount,
            memo=f"{memo} to {allowance.name}" if memo else f"{allowance.name}",
            extra={
                "tag": "allowance",
                "amount": amount,
            },
        )
    except Exception as exc:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc

    return {"payment_hash": payment_hash, "payment_request": payment_request}
