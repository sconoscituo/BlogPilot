"""포트원(PortOne) V2 결제 연동 스켈레톤"""
import httpx
from app.config import config

PORTONE_API_URL = "https://api.portone.io"

async def verify_payment(payment_id: str) -> dict:
    """결제 검증"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{PORTONE_API_URL}/payments/{payment_id}",
            headers={"Authorization": f"PortOne {config.PORTONE_SECRET_KEY}"},
        )
        return response.json()

async def cancel_payment(payment_id: str, reason: str = "사용자 요청") -> dict:
    """결제 취소"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{PORTONE_API_URL}/payments/{payment_id}/cancel",
            headers={"Authorization": f"PortOne {config.PORTONE_SECRET_KEY}"},
            json={"reason": reason},
        )
        return response.json()
