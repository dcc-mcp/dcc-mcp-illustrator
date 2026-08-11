---
name: illustrator-advanced
description: Reach the complete official Illustrator object model through structured DOM references, with explicit raw ExtendScript fallback for API gaps.
license: MIT
compatibility: "Illustrator CEP/ExtendScript; adobepy officialDom"
allowed-tools: Python
metadata:
  dcc-mcp:
    dcc: illustrator
    version: "0.1.0"
    layer: advanced
    stage: scene
    search-hint: "illustrator official dom object model extendscript advanced api create artwork"
    tags: "adobe,illustrator,dom,extendscript"
    tools: tools.yaml
---

# Illustrator Advanced API

Prefer `official_dom`: it performs structured root/get/set/call/construct/keys/
snapshot/release operations without source evaluation. DOM references returned
as `{"$ref": "...", "$type": "..."}` are session-scoped.

Use raw ExtendScript only when the typed facade and official DOM cannot express
the operation. Treat raw source as destructive and inspect it before execution.
