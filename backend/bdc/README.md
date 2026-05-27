# SAP Business Data Cloud (BDC) – POC Data Layer

## Purpose

This folder represents a **BDC-shaped data layer** for the Logistics Assistant POC.

In the target architecture, SAP Business Data Cloud (BDC) provides harmonised,
business-semantic data products across SAP and non-SAP systems (S/4HANA,
Ariba, BW, external logistics platforms).

For this POC, BDC is **mocked**, but the **data contracts and access patterns
are final**.

This ensures the POC is **BDC-ready, not BDC-dependent**.

---

## Contents

``
bdc/
├── models.py
├── seed_data.py
├── data_product.py
└── README.md

---

## models.py

Defines the **six BDC data product contracts** used by the Logistics Assistant:

- Shipment
- Supplier & Alternate Suppliers
- Cross-Entity Inventory Position
- Customer Commitments
- Port & Logistics Events
- Historical Disruption Patterns

These are **pure Pydantic models**:
- no logic
- no queries
- no source-system details

Agents reason **only** over these business-semantic objects.

---

## seed_data.py

Contains **static scenario data** that simulates what BDC would return if live.

This file:
- represents harmonised SAP + non-SAP data
- supports the Shanghai port congestion scenario
- is used **only in the POC**

In production, this file is removed.

---

## data_product.py

This module is the **single access point** to BDC data.

All agents and orchestration logic call functions in this file.
No agent reads `seed_data.py` directly.

In the POC:
- functions read from `seed_data.py`

In production:
- function bodies are replaced with SAP Datasphere OData queries

Function signatures and return types remain unchanged, keeping the swap isolated.

---

## Design Principle

> Agents never query raw SAP tables or non-SAP APIs.
> They reason only over harmonised BDC data products.

This directly addresses the PrismCorp problem of siloed data and manual
decision context assembly.

---

## Status

✅ BDC data layer complete for POC  
✅ Ready to be wired into polling and agents  
✅ No further changes required here