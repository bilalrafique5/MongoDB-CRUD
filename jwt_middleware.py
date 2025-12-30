from fastapi import Request
from fastapi.responses import JSONResponse
from auth_utils import decode_access_token

PUBLIC_PATHS = {
    "/register",
    "/token",
    "/docs",
    "/openapi.json",
    "/redoc"
}

async def jwt_middleware(request: Request, call_next):
    path = request.url.path

    # Allow public routes
    if path in PUBLIC_PATHS:
        return await call_next(request)

    # Protect students routes
    if path.startswith("/students") or path.startswith("/decode-token"):
        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Authorization token missing"}
            )

        token = auth_header.split(" ")[1]
        payload = decode_access_token(token)

        if not payload:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired token"}
            )

        # Attach payload to request
        request.state.user = payload

    return await call_next(request)
