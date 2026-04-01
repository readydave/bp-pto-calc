# Future Plans

## Power Apps Option

An app like this is possible to build in Power Apps, but it is not a 1:1 replacement for the current standalone desktop app.

- Good fit for a Canvas app: PTO forms, date and number inputs, holiday rules, projection calculations, and sortable or filterable result views.
- Recommended backend: Dataverse is the best fit for a fuller internal business app; SharePoint can work for a lighter version.
- Export note: CSV or XLSX export is better treated as a Power Automate assisted workflow than a pure Power Apps client-side feature.
- Main mismatch: Power Apps is primarily a browser and mobile app platform, not a packaged native desktop app in the same style as the current PySide app.
- Local file limitation: Power Apps supports offline and import or export patterns, but it is a weaker fit for user-managed local JSON scenario files and direct local save or load behavior.

Conclusion: this is a good candidate for an internal Microsoft 365 business app, but a poor fit if the goal is full parity with a true standalone desktop app and strong local-file workflows.

## Sources

- https://learn.microsoft.com/en-us/power-apps/maker/canvas-apps/build-responsive-apps
- https://learn.microsoft.com/en-us/power-apps/maker/canvas-apps/working-with-tables
- https://learn.microsoft.com/en-us/power-apps/maker/canvas-apps/offline-apps
- https://learn.microsoft.com/fr-fr/power-platform/power-fx/reference/function-savedata-loaddata
- https://learn.microsoft.com/en-us/power-apps/maker/canvas-apps/controls/control-export-import
- https://learn.microsoft.com/en-us/power-platform/guidance/architecture/real-world-examples/dataverse-canvas-app
