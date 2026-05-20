from sqlalchemy.orm import Session

from app.db.database import engine
from app.db.models import Model
from app.db.seed import seed_admin

Model.metadata.create_all(bind=engine)

with Session(engine) as db:
    seed_admin(db)

print("Tables created")
