"""应用配置模块"""

import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()


class Settings:
    """应用配置"""

    # MongoDB
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://ecnu10234500007:ECNU10234500007@dds-uf6cf83b99151cc4-pub.mongodb.rds.aliyuncs.com:3717/admin")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "ecnu10234500007")

    # JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))

    # 服务
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))


settings = Settings()
