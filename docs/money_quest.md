# LifeQuest Money Quest

Money Quest is LifeQuest's personal finance guardrail module. It is intentionally not a brokerage tool, not a bank integration, and not investment advice.

The first version focuses on three jobs:

- protect important goals such as an emergency fund and hair-transplant fund
- record weekly cashflow so money decisions have context
- keep loan-funded leveraged ETF ideas behind explicit guardrails

## Local Routes

Open the frontend:

```text
http://127.0.0.1:8000/life-admin/money
```

Useful API routes:

```text
GET /money/overview
POST /money/goals
GET /money/goals
POST /money/goals/{goal_ref}/contributions
POST /money/checkins/weekly
POST /money/loan-scenarios
GET /money/loan-scenarios
POST /money/leverage-plans
GET /money/leverage-plans
GET /money/leverage-plans/{plan_ref}/review
POST /money/leverage-plans/{plan_ref}/mark-reviewed
POST /money/leverage-plans/{plan_ref}/decision-log
GET /money/leverage-plans/{plan_ref}/decision-log
```

## Guardrail Defaults

The default Taiwan 2x ETF strategy template is conservative by design:

- market: `tw`
- leveraged asset label: `Taiwan 2x ETF`
- target shape: `50% leveraged ETF / 50% cash`
- rebalance frequency: quarterly
- emergency fund required: 6 months
- max debt service ratio: 20% of monthly income
- minimum cash reserve: 30%
- max strategy drawdown under stress: 35%

These defaults are not a recommendation to invest. They are review thresholds that make risk visible before any real-world action.

## Loan-Funded Strategy Rule

Loan-funded investment plans start as `draft`.

LifeQuest only allows a plan to be marked `reviewed` when there are no failed guardrails. `reviewed` means "this plan passed the local checklist"; it does not mean "this plan is recommended."

The review currently checks:

- latest weekly cashflow exists
- emergency fund covers the required months
- attached loan payment stays under the debt service ratio limit
- protected goals still have enough projected free cashflow
- strategy cash reserve is above the minimum
- ETF drawdown stress scenarios of 30%, 50%, and 70%
- daily reset and volatility risk is shown as an always-visible informational warning

## Daily Game Layer

Money Quest adds two manual daily quests:

- `money-weekly-review`: complete after recording or reviewing cashflow
- `leverage-plan-review`: complete after checking strategy guardrails

The quests reward review behavior, not borrowing, buying, or increasing exposure.
