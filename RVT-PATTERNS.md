
### Type swap on a family instance (Revit-made c3xtsany24, Snowdon Structural 2024, 588559: 588556 -> 588537)
Revit changes FamilyInstance.m_masterSymbolId (588556 -> 588537) AND InstInfoBase.m_symbolId (984678 -> 1028040): a NEW derived-symbol element 1028040 is added (16571 -> 16572 elements), instance 588537 header changes. Writer change_type (same ids, offline) changes only m_masterSymbolId (m_symbolId stays 984678, the old type's derived symbol). Gap: stale m_symbolId; whether Revit tolerates it is being tested by opening the writer output in the VM (c3xtsanywriter24).
