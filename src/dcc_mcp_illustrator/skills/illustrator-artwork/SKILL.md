---
name: illustrator-artwork
description: Inspect Illustrator artwork, edit text frames, and update path geometry and transforms through typed adobepy facades.
license: MIT
compatibility: "Illustrator CEP/ExtendScript; dcc-mcp-core 0.19+"
allowed-tools: Python
metadata:
  dcc-mcp:
    dcc: illustrator
    version: "0.1.0"
    layer: domain
    stage: scene
    search-hint: "illustrator edit path points translate resize rotate text contents artwork"
    tags: "adobe,illustrator,path,text,transform"
    tools: tools.yaml
---

# Illustrator Artwork

Inspect exact named artwork before editing it. Use structured official DOM for
creation or host APIs not covered by the typed mutation facade.
