---
name: illustrator-document
description: Inspect Illustrator documents, artboards, layers, selections, vector items, linked artwork, text, stories, and swatches through typed adobepy facades.
license: MIT
compatibility: "Illustrator CEP/ExtendScript; dcc-mcp-core 0.19+"
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

Inspect the active document before mutations. Item kinds are `page`, `path`,
`compound`, `placed`, `raster`, `text`, `story`, and `swatch`. Names are exact.
