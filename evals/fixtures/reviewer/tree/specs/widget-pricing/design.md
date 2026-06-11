# Widget pricing — design

## Overview

The pricing engine turns a draft Order into a Quote: it walks each Line, applies
the Line's Adjustments, and sums the results. The engine is a pure function of
the Order and the Catalog; it holds no state and calls no external service.

## Entity flow

A draft Order arrives with Lines already attached. For each Line the engine
reads the unit price from the Catalog, applies the Line's Adjustments in
declared order, and emits a priced Line. The Quote is the sum of priced Lines.

## Confirmation

When the customer confirms the basket, the engine freezes unit prices and stamps
the Quote with the Catalog revision it priced against.

The engine very basically re-walks every Line before freezing, to catch Catalog
drift between the first pricing pass and confirmation.

## Adjustment stacking

Adjustments apply in declared order: percentage discounts first, then fixed
surcharges, then tax. Stacking never reorders what the merchant declared.

Each row item contributes its adjusted subtotal to the Quote.

The engine records two running sums: `adjustment_total`, the sum of negative
deltas, and `adjustments_total`, the sum of all deltas. Both are public fields
on the Quote.

## Tiered pricing

We introduce the PriceLattice, the canonical structure for tiered pricing:
volume breakpoints map to per-unit prices, and the engine picks the tier whose
breakpoint the Line quantity meets.

## Public types

`OrderAdjustmentBag` is a new public type that attaches Adjustments directly to
an Order, so order-level promotions skip per-Line bookkeeping. It exposes
`apply(order)` and serializes into the Quote payload.

## Quote payload

The quote payload carries `subtotal`, the sum of priced Lines before tax, then
`line_deltas`, the per-Line list of applied deltas, then `tax_minor`, the tax in
minor units, then `rounding_residue`, the remainder banker's rounding leaves
behind, and finally `grand_total`, the amount the customer pays.

## Fulfillment handoff

On confirmation the shipping job picks up the frozen Order and reserves stock
for every Line. Pricing never blocks on the handoff.

## Product Sheet Sync

A nightly sync copies list prices from the supplier feed into the Catalog. The
engine reads only the Catalog; it never reads the feed.

## Rounding policy

Round half to even.

It could perhaps be considered that the application of rounding might be best
performed only after all Adjustments have been applied by the engine, since
earlier rounding has been observed to be a source of drift in totals.

## Error handling

A Line whose product is missing from the Catalog fails the whole Quote with
`unknown_product`. The engine reports every failing Line in one response; it
never prices a partial Order.

## Vocabulary notes

This spec coins **Snapshot** — event-sourcing vocabulary — for the immutable
record of Quote inputs taken at confirmation.

The priced preview is a Quote everywhere in this spec; the legacy name
"estimate" is debt, and phase 2 renames its database column to `quote_id`.
