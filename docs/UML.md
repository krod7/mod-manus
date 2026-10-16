# Modulo — UML and system diagrams

The Mermaid sources below are editable and render in GitHub. They describe the delivered architecture, including the static/runtime separation.

## Conversion sequence

```mermaid
sequenceDiagram
  actor User
  participant UI as Static workspace
  participant Import as Upload/API adapter
  participant API as Optional Flask API
  participant Bus as Python pipeline
  participant Compiler as Browser compiler
  participant Views as Graph/code views
  User->>UI: Attach one single-page file
  UI->>Import: Validate size and extension
  alt Structured JSON / SVG / draw.io / Mermaid
    Import->>Import: Parse structured graph
    Import-->>UI: Graph and original text
  else PNG / JPEG / PDF
    Import->>API: POST /api/analyze (file)
    API->>Bus: Intake + recognition + structural feedback
    Bus-->>API: Graph + uncertainty warnings
    API-->>Import: Review-required recognition result
    Import-->>UI: Editable graph + original preview
  end
  UI->>Views: Reconstruct and mark issues
  User->>UI: Correct labels/types/arrows; confirm review
  UI->>Compiler: Validate graph and executable grammar
  alt Blocking errors
    Compiler-->>UI: Actionable validation messages
  else Valid graph
    User->>UI: Generate language
    alt Explicitly connected compilation API
      UI->>API: POST /api/convert (graph, language)
      API->>Bus: Logic + pseudocode + code + trace
      Bus-->>UI: Generated artifacts
    else Browser-only
      UI->>Compiler: Compile graph state machine
      Compiler-->>UI: Source + pseudocode + trace
    end
    UI->>Views: Show traceable artifacts
    User->>Views: Select node, arrow, or source line
    Views->>Views: Highlight corresponding regions
  end
```

## Domain classes

```mermaid
classDiagram
  class Graph {
    name: string
    nodes: Node[]
    edges: Edge[]
  }
  class Node {
    id: string
    type: NodeType
    label: string
    x: number
    y: number
    confidence: number
    note: string
  }
  class Edge {
    id: string
    source: NodeId
    target: NodeId
    label: string
  }
  class Instruction {
    kind: string
    variable: string
    expression: ValidatedExpression
    inputType: string
  }
  class TraceEntry {
    nodeId: string
    edgeId: optional string
    codeLines: integer[]
    pseudoLines: integer[]
  }
  class ConversionResult {
    language: string
    code: string
    pseudocode: string
    validation: Validation
    trace: TraceEntry[]
  }
  Graph "1" *-- "1..100" Node
  Graph "1" *-- "0..300" Edge
  Node "1" --> "1" Instruction : interpreted as
  ConversionResult "1" --> "1" Graph
  ConversionResult "1" *-- "many" TraceEntry
  TraceEntry --> Node : stable ID
  TraceEntry --> Edge : optional ID
```

## Workspace states

```mermaid
stateDiagram-v2
  [*] --> ExampleReady
  ExampleReady --> Importing: attach file
  Importing --> ImportError: invalid/unavailable API
  ImportError --> Importing: replace file
  Importing --> Review: parsed/recognized graph
  Review --> Review: edit / validate
  Review --> Compiling: valid + review confirmed
  Compiling --> GenerationError: compiler/API failure
  GenerationError --> Review: repair / retry
  Compiling --> Traceable: actual output returned
  Traceable --> Review: edit logic
  Traceable --> Simulating: supply inputs
  Simulating --> Traceable: output or bounded runtime error
  Traceable --> Importing: attach new flow
```

## Deployment separation

```mermaid
flowchart LR
  User[User browser] --> Pages[GitHub Pages: frontend/]
  Pages --> Local[Local graph compiler / interpreter]
  User -->|optional HTTPS API origin| API[Python host: Flask API]
  API --> OCR[OpenCV + Tesseract + PDF rasterizer]
  API --> Pipeline[Validation / logic / codegen / trace]
  Local --> Storage[Browser localStorage: graphs + notes]
  User --> Export[Download JSON / SVG / source]
```
