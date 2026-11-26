from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DataError, IntegrityError, OperationalError, SQLAlchemyError
from app.routers import auth, lost, skills, confessions, food
from app.services.lost_images import UPLOAD_DIR

app = FastAPI(title='BIRGE Campus Community API',version='1.1.0',description='REST API for Lost & Found, Däm, SkillQos, and Ishimде')
app.add_middleware(CORSMiddleware,allow_origins=['*'],allow_methods=['*'],allow_headers=['*'])
app.include_router(auth.router)
app.include_router(lost.router)
app.include_router(skills.router)
app.include_router(confessions.router)
app.include_router(food.router)

@app.exception_handler(SQLAlchemyError)
async def handle_database_error(_request: Request, error: SQLAlchemyError):
    if isinstance(error, IntegrityError):
        return JSONResponse(status_code=409, content={'detail': 'Data conflicts with existing records or constraints'})
    if isinstance(error, DataError):
        return JSONResponse(status_code=422, content={'detail': 'Value cannot be stored'})
    if isinstance(error, OperationalError):
        return JSONResponse(status_code=503, content={'detail': 'Database unavailable; please retry'})
    return JSONResponse(status_code=500, content={'detail': 'Unable to complete the database operation'})

@app.get('/')
def home():
    return {'app':'BIRGE API','docs':'/docs','status':'running'}

FRONTEND = Path(__file__).resolve().parent.parent / 'frontend'
ASSETS = FRONTEND.parent / 'static'
ASSETS.mkdir(exist_ok=True)
app.mount('/uploads/lost_items', StaticFiles(directory=UPLOAD_DIR), name='lost-images')
app.mount('/static/images', StaticFiles(directory=ASSETS / 'images'), name='images')
app.mount('/static/fonts', StaticFiles(directory=ASSETS / 'fonts'), name='fonts')
app.mount('/static', StaticFiles(directory=FRONTEND), name='static')

app.mount('/app', StaticFiles(directory=FRONTEND, html=True), name='frontend')
