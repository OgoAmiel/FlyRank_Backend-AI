from unittest.mock import AsyncMock, Mock
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

import jobs_api.main as jobs_main
import asyncio


def test_create_report(monkeypatch, tmp_path):
    # Create an isolated, in-memory test database
    test_db = tmp_path / "test_reports.db"

    test_engine = create_engine(
        f"sqlite:///{test_db}",
        connect_args={"check_same_thread": False},
    )

    SQLModel.metadata.create_all(test_engine)

    # Replace the production database engine
    monkeypatch.setattr(jobs_main, "engine", test_engine)

    # Prevent sending a real event to Inngest
    mock_send = AsyncMock()
    monkeypatch.setattr(
        jobs_main.inngest_client,
        "send",
        mock_send,
    )

    client = TestClient(jobs_main.app)

    response = client.post(
        "/reports",
        json={"topic": "Artificial Intelligence"},
    )

    assert response.status_code == 202

    data = response.json()

    assert data["status"] == "pending"
    assert "id" in data

    # Confirm the report was saved in the test database
    with Session(test_engine) as session:
        report = session.get(jobs_main.ReportJob, data["id"])

        assert report is not None
        assert report.topic == "Artificial Intelligence"
        assert report.status == "pending"

    with Session(test_engine) as session:
        events = session.exec(
            select(jobs_main.OutboxEvent)
            ).all()

        assert len(events) == 1

        event = events[0]

        assert event.event_name == "report/requested"
        assert event.status == "pending"
        assert event.payload["id"] == data["id"]
        assert event.payload["topic"] == "Artificial Intelligence"

        mock_send.assert_not_awaited()

        test_engine.dispose()


def test_get_report(monkeypatch):
    # Create an isolated test database
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    SQLModel.metadata.create_all(test_engine)

    # Replace the production engine
    monkeypatch.setattr(jobs_main, "engine", test_engine)

    # Insert a sample report
    report = jobs_main.ReportJob(
        topic="Machine Learning",
        status="done",
        result={
            "summary": "Report about Machine Learning",
            "topic": "Machine Learning",
        },
    )

    with Session(test_engine) as session:
        session.add(report)
        session.commit()
        report_id = report.id

    # Test the GET endpoint
    client = TestClient(jobs_main.app)

    response = client.get(f"/reports/{report_id}")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == report_id
    assert data["topic"] == "Machine Learning"
    assert data["status"] == "done"
    assert data["result"]["summary"] == "Report about Machine Learning"

    test_engine.dispose()


def test_get_report_not_found(monkeypatch):
    # Create an isolated test database
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    SQLModel.metadata.create_all(test_engine)

    # Replace the production database engine
    monkeypatch.setattr(jobs_main, "engine", test_engine)

    # Create a test client
    client = TestClient(jobs_main.app)

    # Request a report that doesn't exist
    response = client.get("/reports/nonexistent-report-id")

    # Verify the API returns 404
    assert response.status_code == 404
    assert response.json()["detail"] == "Report not found"

    test_engine.dispose()


def test_make_report_success(monkeypatch):
    # Create an isolated test database
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    SQLModel.metadata.create_all(test_engine)

    monkeypatch.setattr(jobs_main, "engine", test_engine)

    # Create a pending report
    report = jobs_main.ReportJob(
        topic="Python Programming",
        status="pending",
    )

    with Session(test_engine) as session:
        session.add(report)
        session.commit()
        report_id = report.id

    # Mock Inngest's step execution
    async def fake_run(step_name, function):
        return function()

    mock_sleep = AsyncMock()
    mock_run = AsyncMock(side_effect=fake_run)

    # Create a fake Inngest context
    ctx = SimpleNamespace(
        event=SimpleNamespace(
            data={
                "id": report_id,
                "topic": "Python Programming",
            }
        ),
        step=SimpleNamespace(
            sleep=mock_sleep,
            run=mock_run,
        ),
        logger=Mock(),
    )

    # Execute the background function
    asyncio.run(jobs_main.make_report._handler(ctx))

    # Verify the report was updated
    with Session(test_engine) as session:
        updated_report = session.get(
            jobs_main.ReportJob,
            report_id,
        )

        assert updated_report is not None
        assert updated_report.status == "done"
        assert updated_report.result == {
            "summary": "Report about Python Programming",
            "topic": "Python Programming",
        }

    # Verify Inngest steps were called
    mock_sleep.assert_awaited_once()
    mock_run.assert_awaited_once()

    test_engine.dispose()


def test_mark_report_failed(monkeypatch):
    # Create an isolated test database
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    SQLModel.metadata.create_all(test_engine)

    monkeypatch.setattr(jobs_main, "engine", test_engine)

    # Create a pending report
    report = jobs_main.ReportJob(
        topic="Failed Report Test",
        status="pending",
    )

    with Session(test_engine) as session:
        session.add(report)
        session.commit()
        report_id = report.id

    # Simulate Inngest's failure event
    ctx = SimpleNamespace(
        event=SimpleNamespace(
            data={
                "event": {
                    "data": {
                        "id": report_id,
                        "topic": "Failed Report Test",
                    }
                }
            }
        ),
        logger=Mock(),
    )

    # Execute the failure handler
    asyncio.run(jobs_main._mark_report_failed(ctx))

    # Verify PostgreSQL status was updated
    with Session(test_engine) as session:
        updated_report = session.get(
            jobs_main.ReportJob,
            report_id,
        )

        assert updated_report is not None
        assert updated_report.status == "failed"
        assert updated_report.result is None
        assert updated_report.updated_at >= updated_report.created_at

    ctx.logger.info.assert_called_once()

    test_engine.dispose()


def test_create_report_when_inngest_fails(monkeypatch, tmp_path):
    test_db = tmp_path / "test_inngest_failure.db"

    test_engine = create_engine(
        f"sqlite:///{test_db}",
        connect_args={"check_same_thread": False},
    )

    SQLModel.metadata.create_all(test_engine)

    monkeypatch.setattr(jobs_main, "engine", test_engine)

    # Simulate Inngest being unavailable
    mock_send = AsyncMock(
        side_effect=Exception("Inngest unavailable")
    )

    monkeypatch.setattr(
        jobs_main.inngest_client,
        "send",
        mock_send,
    )

    client = TestClient(jobs_main.app)

    response = client.post(
        "/reports",
        json={"topic": "Network Failure Test"},
    )

    # API should accept the request despite Inngest being down
    assert response.status_code == 202

    data = response.json()
    assert data["status"] == "pending"

    with Session(test_engine) as session:
        report = session.get(jobs_main.ReportJob, data["id"])

        assert report is not None
        assert report.status == "pending"

        events = session.exec(
            select(jobs_main.OutboxEvent)
        ).all()

        assert len(events) == 1
        assert events[0].status == "pending"
        assert events[0].payload["id"] == data["id"]

    # The API must not attempt direct event delivery
    mock_send.assert_not_awaited()

    test_engine.dispose()