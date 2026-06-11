"""把 model_configs / service_configs 中的历史密文一次性迁移为明文存储。

必须在 SECRET_KEY 与密文写入时一致的环境下执行：

    python -m app.tools.migrate_secrets

幂等：已是明文的行原样跳过，可重复执行。
迁移完成后，存量数据与 SECRET_KEY 彻底解耦，之后轮换 SECRET_KEY
只影响登录态（JWT），不再影响模型与服务配置。
"""

from sqlalchemy import select

from app.core.security import decrypt_secret, mask_secret
from app.db.models import ModelConfig, ServiceConfig
from app.db.session import SessionLocal


def main() -> None:
    migrated = 0
    skipped = 0
    with SessionLocal() as db:
        for row in db.scalars(select(ModelConfig).where(ModelConfig.api_key_encrypted.is_not(None))):
            plain = decrypt_secret(row.api_key_encrypted)
            if plain == row.api_key_encrypted:
                skipped += 1
                continue
            row.api_key_encrypted = plain
            db.add(row)
            migrated += 1
            print(f"model_config id={row.id} purpose={row.purpose}: {mask_secret(plain)}")
        for row in db.scalars(select(ServiceConfig)):
            plain = decrypt_secret(row.config_encrypted)
            if plain == row.config_encrypted:
                skipped += 1
                continue
            row.config_encrypted = plain
            db.add(row)
            migrated += 1
            print(f"service_config id={row.id} type={row.service_type}: 已转明文")
        db.commit()
    print(f"完成：{migrated} 行已转为明文，{skipped} 行已是明文跳过。")


if __name__ == "__main__":
    main()
