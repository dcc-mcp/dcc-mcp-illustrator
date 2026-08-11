from dcc_mcp_illustrator.capabilities import illustrator_capabilities


def test_illustrator_declares_bridge_domain_capabilities():
    capabilities = illustrator_capabilities()
    assert capabilities.scene_info is True
    assert capabilities.snapshot is True
    assert capabilities.file_operations is True
    assert capabilities.selection is True
    assert capabilities.scene_manager is True
    assert capabilities.transform is True
    assert capabilities.render_capture is True
    assert capabilities.hierarchy is True
    assert capabilities.has_embedded_python is False
    assert capabilities.bridge_kind == "adobepy_broker"
    assert capabilities.extensions["official_dom"] is True
