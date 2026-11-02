# ADR 003: TiDB Cloud PostgreSQL

## Status

Accepted

## Decision

Ứng dụng dùng PostgreSQL-compatible TiDB Cloud, database `cyverse_internal`, thông qua PostgreSQL wire protocol trên port `5432` và TLS. SQLAlchemy 2.0 cùng psycopg 3 phục vụ API, repositories, workers và Alembic.

`DATABASE_URL` là cấu hình kết nối duy nhất, bắt buộc ở backend. Thông tin xác thực chỉ nằm trong `.env` bị Git ignore hoặc secret environment của dịch vụ triển khai. Frontend truy cập dữ liệu qua API, không giữ thông tin kết nối database. Authentication do FastAPI quản lý.

## Consequences

Giữ nguyên models và lịch sử Alembic; đổi nhà cung cấp không làm thay đổi application schema. Migration phải chạy trên database đích trước khi sử dụng ứng dụng. Cần xác minh tính tương thích của schema, transactions, JSONB và advisory locks trên instance trước khi đưa vào vận hành.

Tài liệu nhà cung cấp: [Quick start](https://docs.pingcap.com/tidbcloud/pg-quickstart/) và [PostgreSQL compatibility](https://docs.pingcap.com/tidbcloud/postgresql-compatibility/).
