from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware


from app.core.rate_limit import limiter
from app.routers.auth import router as auth_router
from app.routers.profile import router as profile_router
from app.routers.activation import router as activation_router
from app.routers.ws import router as web_socket
from app.routers.admin_vms import router as admin_vms_router
from app.routers.user_vms import router as user_vms_router




app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],

    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(web_socket)
app.include_router(activation_router)
app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(admin_vms_router)
app.include_router(user_vms_router)




@app.get("/")
@limiter.exempt
def health(request: Request):

    return {

        "status": "ok"

    }


