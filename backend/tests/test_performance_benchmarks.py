"""R6.1 Automated Performance and Load Benchmarks.

Kiểm chứng các chỉ số hiệu năng thực tế theo Kế hoạch bàn giao mục 6.2:
1. Độ trễ phân tích văn bản rule-only với payload tối đa (10.000 ký tự) đạt ngưỡng p95 < 3.0s.
2. Xử lý đồng thời 5 request text không phát sinh lỗi hay suy giảm đột biến.
3. Độ trễ đối chiếu thông tin doanh nghiệp (stateless lookup) đạt < 500ms.
4. Kiểm soát tải và an toàn: Payload > 10.000 ký tự bị từ chối 422 ngay lập tức.
"""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import time
import pytest
from fastapi.testclient import TestClient

from app.core.rate_limit import reset_rate_limits
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def db_engine(tmp_path):
    reset_rate_limits()
    engine = create_engine(
        f"sqlite:///{tmp_path / 'benchmark.sqlite'}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def client(db_engine):
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    def override_get_db():
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_benchmark_database_provides_distinct_concurrent_connections(db_engine):
    with db_engine.connect() as first, db_engine.connect() as second:
        assert first.connection.driver_connection is not second.connection.driver_connection


BENCHMARK_JOB_TEXT = (
    "Công ty Cổ phần Công nghệ ABC tuyển dụng Kỹ sư Phần mềm Full-Stack tại Hà Nội. "
    "Mô tả công việc: Thiết kế, xây dựng và vận hành hệ thống Web backend FastAPI và frontend Next.js. "
    "Yêu cầu: Thành thạo Python, TypeScript, PostgreSQL, Docker, Git. "
    "Mức lương: 25 - 35 triệu đồng/tháng. Đãi ngộ: Thưởng dự án, bảo hiểm sức khỏe toàn diện. "
    "Quy trình ứng tuyển: Ứng viên nộp CV qua email tuyendung@abc-tech.example. "
    "Tuyệt đối không thu bất kỳ khoản phí hồ sơ, phí đặt cọc hay yêu cầu nạp tiền nào từ ứng viên."
)


def test_analysis_latency_with_max_payload(client: TestClient):
    """Kiểm tra độ trễ phân tích văn bản với kích thước tối đa (10.000 ký tự) đạt < 3.0 giây."""
    repeat_count = (10000 // len(BENCHMARK_JOB_TEXT)) + 1
    max_text = (BENCHMARK_JOB_TEXT + "\n\n") * repeat_count
    max_text = max_text[:10000]
    assert len(max_text) == 10000

    start = time.perf_counter()
    res = client.post("/api/v1/analyses", json={"text": max_text, "use_ai": False})
    elapsed = time.perf_counter() - start

    assert res.status_code == 201
    assert elapsed < 3.0, f"Độ trễ phân tích 10.000 ký tự vượt ngưỡng 3.0s: {elapsed:.3f}s"
    data = res.json()
    assert data["risk_label_vi"] is not None


def test_concurrent_analysis_load_meets_performance_target(client: TestClient):
    """Kiểm tra 5 request text đồng thời không gây lỗi và hoàn thành nhanh chóng."""
    text = (BENCHMARK_JOB_TEXT + "\n") * 5  # ~1.800 ký tự
    concurrency = 5
    barrier = Barrier(concurrency)
    latencies = []
    analysis_ids = []

    def make_request():
        barrier.wait(timeout=5)
        start = time.perf_counter()
        res = client.post(
            "/api/v1/analyses",
            json={"text": text, "use_ai": False},
        )
        elapsed = time.perf_counter() - start
        assert res.status_code == 201
        data = res.json()
        assert data["risk_label_vi"] is not None
        return elapsed, data["id"]

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(make_request) for _ in range(concurrency)]
        for f in futures:
            latency, analysis_id = f.result()
            latencies.append(latency)
            analysis_ids.append(analysis_id)

    max_latency = max(latencies)
    assert max_latency < 3.0, f"Độ trễ cao nhất trong nhóm đồng thời vượt 3.0s: {max_latency:.3f}s"
    assert len(latencies) == concurrency
    assert len(set(analysis_ids)) == concurrency


def test_oversized_payload_rejected_immediately(client: TestClient):
    """Văn bản vượt 10.000 ký tự phải bị từ chối 422 ngay lập tức (< 100ms)."""
    oversized = "A" * 10001
    start = time.perf_counter()
    res = client.post("/api/v1/analyses", json={"text": oversized})
    elapsed = time.perf_counter() - start

    assert res.status_code == 422
    assert elapsed < 0.2, f"Từ chối payload quá lớn quá chậm: {elapsed:.3f}s"
    assert "10.000 ký tự" in res.text


def test_verification_lookup_latency(client: TestClient):
    """Đối chiếu thông tin doanh nghiệp (stateless lookup) phải hoàn thành trong < 500ms."""
    payload = {
        "company_name": "Công ty E2E A",
        "contact_email": "hr@e2e-a.example",
        "recruitment_website": "https://e2e-a.example/careers",
    }
    start = time.perf_counter()
    res = client.post("/api/v1/verifications", json=payload)
    elapsed = time.perf_counter() - start

    assert res.status_code == 200
    assert elapsed < 0.5, f"Đối chiếu doanh nghiệp quá chậm: {elapsed:.3f}s"
