"""
FastAPI application for the Regulatory Compliance Document Review Environment.
Uses openenv-core create_app for spec compliance.
"""
try:
    from openenv.core.env_server.http_server import create_app
except Exception as e:
    raise ImportError(
        "openenv is required. Install with: uv sync"
    ) from e

try:
    from ..models import Action as ComplianceAction
    from ..models import Observation as ComplianceObservation
    from .compliance_environment import ComplianceReviewEnvironment
except (ImportError, ModuleNotFoundError):
    from env.models import Action as ComplianceAction
    from env.models import Observation as ComplianceObservation
    from server.compliance_environment import ComplianceReviewEnvironment

app = create_app(
    ComplianceReviewEnvironment,
    ComplianceAction,
    ComplianceObservation,
    env_name="compliance_review",
    max_concurrent_envs=1,
)


def main(host: str = "0.0.0.0", port: int = 7860):
    """
    Entry point for direct execution via uv run or python -m.
    """
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=7860)
    args = parser.parse_args()
    main()
