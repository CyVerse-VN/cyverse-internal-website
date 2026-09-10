# Kiến trúc

Hệ thống là monorepo gồm frontend Next.js và backend FastAPI theo hướng modular monolith. Các tác vụ dài được chuyển sang background jobs; scheduler chịu trách nhiệm kích hoạt các job định kỳ.

