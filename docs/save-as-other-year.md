# Save As another Revit year (feasibility note, rung 7, c3x-rvttype)

Verdict: not feasible as a byte-level operation; do not offer it.

- Revit itself only upgrades (open an older file in a newer Revit, Save As); it can never write an older year. So "downgrade" has no oracle at all.
- Every year ships its own Formats/Latest class schema (field lists differ per year, element streams are laid out from it) and its own BasicFileInfo/version stamps. A writer would have to re-lay every element record of every class under the target schema. Our writer is verified for 2024-2026 only and patches records in place; it does not re-lay whole files.
- Upgrade by Revit is the supported route: open the file in the target-year Revit VM, SaveAs, then edit the upgraded file with our writer. Measured elsewhere: Revit resave rewrites most streams (noise floor), so the output is a different file, not an edit.
- Decision: SaveAs-other-year stays refused (unsupported_version / not offered). Revisit only if a schema-to-schema record converter is justified by a real need.
