---
name: illustrator-export
description: Save and export Illustrator documents through typed adobepy facades with explicit absolute paths and format options.
license: MIT
compatibility: "Illustrator CEP/ExtendScript; dcc-mcp-core 0.19+"
allowed-tools: Python
metadata:
  dcc-mcp:
    dcc: illustrator
    version: "0.1.0"
    layer: domain
    stage: export
    search-hint: "illustrator save export ai pdf eps png jpeg svg"
    tags: "adobe,illustrator,save,export"
    tools: tools.yaml
---

# Illustrator Export

Use absolute output paths. `save_document` saves in place when no path is
provided. `export_document` supports native save-as formats and export formats.
