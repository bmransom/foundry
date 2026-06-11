# Widget-shop glossary — the ubiquitous language

The vocabulary contract for this repo's specs, code, and docs. When code and this
file disagree, this file wins (and the code is debt to be migrated). A new term
names its prior art — the industry or stack standard it follows — or records why
none fits.

## Entity model

An **Order** holds **Lines**; a **Line** holds **Adjustments**. Adjustments never
attach to an Order directly — every price delta belongs to the Line it changes.

## Canonical terms

| Term | Definition | Replaces (now debt) |
|---|---|---|
| **Order** | A customer's confirmed purchase; the aggregate root. | basket, cart |
| **Line** | One product entry on an Order: product, quantity, unit price. | row item, order row |
| **Adjustment** | A signed price delta attached to a Line: discount, surcharge, or tax. | modifier, price tweak |
| **Quote** | The computed price of an Order before confirmation. | estimate |
| **Fulfillment** | The process that moves a confirmed Order to delivered. | shipping job |
| **Catalog** | The set of purchasable products and their list prices. | product sheet |
