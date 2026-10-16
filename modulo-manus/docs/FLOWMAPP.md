# How Modulo applies FlowMapp’s workflow principles

FlowMapp’s [User Flow Diagrams reference](https://www.flowmapp.com/features/user-flow-ux-tool), read on 2026-10-16, describes diagram building with shapes, lines and icons; embedded images; element customization; flexible connections; an 80+ icon library; real-time collaboration; multiple flows; project sharing; and export. Its explanatory sections also mention notes and connections between sitemaps and flows. These are claims from that reference, not an exhaustive inventory of every FlowMapp product capability. [1]

Modulo adopts the **common visual mapping functions**, with its own implementation and brand. It reconstructs shapes and arrows, makes elements editable and inspectable, adds node notes and appearance controls, supports multiple local flows, and exports portable JSON/SVG/source files. Its original-file preview supports review against imported images rather than embedding collaborative image objects in a canvas. Stable element IDs extend visual navigation into code and pseudocode traceability.

**The delivered app is not a full FlowMapp clone.** It does not copy proprietary UI code, artwork or the commercial icon library. Realtime multiplayer, cloud-hosted project sharing, sitemap integration and full UX/wireframing functionality are not included. File export/import provides manual sharing and local browser projects provide multiple flows, but neither is represented as live collaboration.

FlowMapp organizes user journeys; Modulo additionally requires executable logic. A box called “Checkout” or “Send email” can communicate intent in a user-flow tool, but it does not define a program. Modulo therefore validates explicit inputs, assignments, conditions and outputs, warns about missing/uncertain paths, and blocks unspecified named tasks instead of generating placeholders.

[GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/about-github-pages) serves static HTML/CSS/JavaScript. That constraint determines Modulo’s browser-first workspace and separate optional Python API. It does not imply that Python image recognition or multiplayer can run on Pages itself. [2]

## References

[1]: https://www.flowmapp.com/features/user-flow-ux-tool "FlowMapp User Flow Diagrams features"
[2]: https://docs.github.com/en/pages/getting-started-with-github-pages/about-github-pages "GitHub documentation: What is GitHub Pages?"
