from pathlib import Path
from unittest import mock

import dcc_mcp_core
from adobe.runtime import BrokerHandle

from dcc_mcp_illustrator.config import IllustratorConfig
from dcc_mcp_illustrator.runtime import IllustratorStatus
from dcc_mcp_illustrator.server import IllustratorMcpServer


def test_server_uses_host_rpc_for_readiness_and_owned_broker_lifecycle():
    broker = BrokerHandle("http://127.0.0.1:47391", "token")
    broker.stop = mock.Mock()
    broker_factory = mock.Mock(return_value=broker)
    readiness_probe = mock.Mock(
        return_value=IllustratorStatus(True, version="30.0.0", target="default")
    )
    server = IllustratorMcpServer(
        gateway_port=0,
        config=IllustratorConfig(timeout=1.0, poll_interval=60.0),
        broker_factory=broker_factory,
        readiness_probe=readiness_probe,
    )
    server.update_gateway_metadata = mock.Mock()
    with mock.patch("dcc_mcp_illustrator.server.DccServerBase.start", return_value=object()):
        server.start(install_atexit_hook=False)
    assert server.bridge_status.ready is True
    assert server._readiness.probe.report()["dcc"] is True
    server.update_gateway_metadata.assert_called_once_with(scene="bridge_ready", version="30.0.0")
    broker_factory.assert_called_once_with(broker_url=None, token=None, timeout=1.0)
    with mock.patch("dcc_mcp_illustrator.server.DccServerBase.stop"):
        server.stop()
    broker.stop.assert_called_once_with()


def test_server_registers_persistent_in_process_skill_executor():
    server = IllustratorMcpServer(
        gateway_port=0,
        config=IllustratorConfig(timeout=1.0, poll_interval=60.0),
    )

    assert server._inprocess_executor_registered is True
    assert server._standalone_main_thread is True

    core_skills = Path(dcc_mcp_core.__file__).resolve().parent / "skills"
    server.run_registration(
        extra_skill_paths=[str(core_skills)],
        include_bundled=False,
    )

    assert server.load_skill("ui-control") is True
    assert server.is_skill_loaded("ui-control") is True
