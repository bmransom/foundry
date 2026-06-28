> **Status:** Ready — fixture for the spec-convergence eval (a seeded blocking defect).

# Design — fixture component

## Overview

The component stores records and exposes a **read-only** path.

SEEDED-DEFECT-CONTRADICT: this Overview calls the path **read-only**, but the Components
table below gives the reader a **delete** responsibility — a direct internal contradiction
(a blocking contract violation) the loop must resolve before it can honestly report
`SPEC_REVIEW: CLEAN`.

## Components

| Component | Purpose |
|---|---|
| store | holds records |
| reader | exposes the read path and deletes expired records |
