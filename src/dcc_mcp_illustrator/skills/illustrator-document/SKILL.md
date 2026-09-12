---
name: illustrator-document
description: Create and inspect Illustrator documents, artboards, layers, selections, vector items, linked artwork, text, stories, and swatches through typed adobepy facades.
license: MIT
compatibility: "Illustrator CEP/ExtendScript; dcc-mcp-core >=0.20.14,<1.0.0"
allowed-tools: Python
metadata:
  dcc-mcp:
    dcc: illustrator
    version: "0.1.0"
    layer: domain
    stage: scene
    search-hint: "illustrator document artboard layer selection path compound placed raster text story swatch"
    tags: "adobe,illustrator,document,vector"
    tools: tools.yaml
---

# Illustrator Document

## Installation and readiness

Use the adapter-owned installation guide for packaged installs, generated CEP
bridges, receipts, upgrades, and uninstall. For an Internal deployment with an
approved prebuilt CEP bridge:

1. Run `dcc-mcp-cli doctor` to inspect the local CLI and gateway.
2. Run `dcc-mcp-cli install --dcc-type illustrator` with the bridge root in
   `--plugin-source` and the Adobe CEP extension root in
   `--adobe-debug-root`. Internal profiles may provide
   `DCC_MCP_PLUGIN_SOURCE` and `DCC_MCP_ADOBE_DEBUG_ROOT`.
3. Restart Illustrator if it has cached the extension.
4. Run `dcc-mcp-cli list` and
   `dcc-mcp-cli wait-ready --dcc-type illustrator` before loading this skill.

The bridge root must contain its manifest and be selected by an approved
catalog or Internal descriptor. This skill does not create links, copy bridge
files, or treat a filesystem link as proof of a loaded CEP session. Confirm
readiness through the CLI and adapter status.

Create an explicit RGB/CMYK document or inspect the active document before mutations. Item kinds are `page`, `path`,
`compound`, `placed`, `raster`, `text`, `story`, and `swatch`. Names are exact.
