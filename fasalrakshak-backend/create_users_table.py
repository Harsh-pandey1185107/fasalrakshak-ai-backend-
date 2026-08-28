from app.core.database import engine
from app.models.user import User

print("Creating users table...")

User.metadata.create_all(
    bind=engine,
    tables=[User.__table__],
)

print("Users table created successfully.")
