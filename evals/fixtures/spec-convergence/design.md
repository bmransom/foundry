> **Status:** Ready — fixture for the spec-convergence eval (a seeded house-style defect).

# Design — fixture component

## Overview

The component stores records and exposes a read path.

SEEDED-DEFECT-HEDGE: arguably it should probably be noted that this design might,
in some cases, perhaps be considered reasonable — a hedged, passive sentence the
spec-convergence loop must remove before it can honestly report `SPEC_REVIEW: CLEAN`.

## Components

| Component | Purpose |
|---|---|
| store | holds records |
| reader | exposes the read path |
