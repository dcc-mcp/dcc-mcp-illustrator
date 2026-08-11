from dcc_mcp_illustrator.cli import build_parser


def test_cli_parses_runtime_configuration():
    args = build_parser().parse_args(
        [
            "--mcp-port",
            "0",
            "--gateway-port",
            "9765",
            "--broker-url",
            "http://127.0.0.1:47391",
            "--no-builtins",
        ]
    )
    assert args.mcp_port == 0
    assert args.gateway_port == 9765
    assert args.broker_url == "http://127.0.0.1:47391"
    assert args.no_builtins is True
