from pathlib import Path

import yaml


def test_render_yaml_validity():
    render_file = Path("render.yaml")
    assert render_file.exists(), "render.yaml does not exist"

    with open(render_file) as f:
        config = yaml.safe_load(f)

    assert "services" in config, "render.yaml must define services"
    services = config["services"]
    assert len(services) == 3, "render.yaml must define exactly 3 services"

    service_names = [s["name"] for s in services]
    assert "spark-daemon" in service_names
    assert "chatlens-backend" in service_names
    assert "chatlens-frontend" in service_names

    for service in services:
        if service["name"] == "spark-daemon":
            assert service["type"] == "worker"
            env_vars = {v["key"]: v.get("value") for v in service.get("envVars", [])}
            assert "SPARK_TIMETABLE" in env_vars
            assert env_vars["SPARK_TIMETABLE"] == "data/timetable_T05.toml"
        elif service["name"] == "chatlens-backend":
            assert service["type"] == "web"
            assert service["healthCheckPath"] in ["/api/healthz", "/healthz", "/api/health"]
        elif service["name"] == "chatlens-frontend":
            assert service["type"] == "web"
            assert service["env"] == "static"
