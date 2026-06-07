# Morpho Midnight — Cantina Audit Recon Map

> Recon notes to prioritize review. **Not** a claim of confirmed bugs. Always
> verify scope and rules on the official competition page before working.

## Scope Summary

- **Competition:** Morpho Midnight (Cantina), status **live**
- **Pool:** up to **$400,000 USDC**. Tiered: **$150k** if max severity is Medium, **$400k** if any valid High. **$20k** for Low/Info (top-5 by quality). KYC required.
- **Window:** 2026-05-29 → **2026-06-12 20:00 UTC**
- **Repo / commit:** `morpho-org/midnight` @ `7538c438513622721e23a94676b93a335b83dace` (HEAD: "More precise `maxRepaid` computation #944")
- **In scope:** `src` only (~2,495 LoC, ~1,400 logic). Mandatory POC for High/Medium (starter: `test/BaseTest.sol`).
- **Heavy prior coverage:** multiple paid audits + Certora formal verification. **2,157 findings already submitted.** Crowded contest.

## Confirmed In-Scope Files

**Core**
- `src/Midnight.sol` — 981 — entire protocol: markets, offers/take, collateral, liquidation, fees, slashing, roles.

**Libraries (`src/libraries`)**
- `UtilsLib.sol` (89), `TickLib.sol` (69), `ConstantsLib.sol` (53), `IdLib.sol` (42), `SafeTransferLib.sol` (35), `EventsLib.sol` (34)

**Ratifiers (`src/ratifiers`)**
- `HashLib.sol` (139), `EcrecoverRatifier.sol` (47), `SetterRatifier.sol` (38)

**Periphery (`src/periphery`)**
- `MidnightBundles.sol` (399), `EcrecoverAuthorizer.sol` (49), `ConsumableUnitsLib.sol` (24), `TakeAmountsLib.sol` (48)

## Architecture

Non-custodial **fixed-rate, fixed-maturity** lending. Lending/borrowing modeled as trading **credit units** (lender claim) and **debt units** (borrower obligation), each ≈ a zero-coupon bond redeemable 1:1 at maturity. Price (a tick ≤ 1 WAD) is the discount; implied yield `(1-price)/price`. Markets are isolated, immutable, permissionlessly created (params hashed into a CREATE2/SSTORE2 address). Order-book/offer settlement model rather than a pool. Up to 128 collaterals/market, 16 active/borrower.

**Trust boundaries / external calls:** oracles (`IOracle.price()`), gates (enter/liquidator), ratifiers, callbacks (`onBuy/onSell/onRepay/onLiquidate/onFlashLoan`), arbitrary ERC-20s. Reentrancy on `take`'s seller blocked via a transient-storage lock; **no global reentrancy guard** otherwise.

## Ranked Review Checklist

**Tier 1 — most likely to hide a High**
1. **`liquidate` math & RCF / bad-debt socialization** (`Midnight.sol` ~581-720). Rounding-direction mismatches in `maxDebt`/`badDebt`; `lossFactor` precision near `totalUnits≈badDebt`; the **freshly-rewritten `maxRepaid` formula** (last commit #944 — lowest duplication odds); `lltv==WAD` special case.
2. **`take` ordering, fee rounding, liquidation lock** (~337-478). Settlement fee has no defined rounding direction (dev-flagged manipulable); `pendingFee` proration; can the transient lock be abused to dodge the seller health check, or a re-entrant `take` corrupt `consumed`/`totalUnits`?
3. **Oracle handling & multi-collateral health** (`isHealthy` ~944-961). `> uint128.max` quoted collateral bricks liquidate/withdraw/take (dev-admitted); one reverting oracle DoS-ing liquidation; self-poison via `supplyCollateral` (no oracle call) to block liquidation.

**Tier 2 — strong Medium candidates**
4. **Continuous-fee & slashing accrual** (~797-851): slash-then-accrue order; adversarial interleaving of `take`/`withdraw`/`updatePosition`.
5. **`take` group/consumed accounting & offer caps** (~337-372): cross-offer `consumed` inconsistencies; in-scope variants of the disclosed stale-`consumed` issue.
6. **Tick/price library** (`TickLib.sol`): `wExp` approximation monotonicity; `tickToPrice`/`priceToTick` inverse-consistency; `MAX_TICK=5820` boundaries; tick-spacing refinement.
7. **`MidnightBundles` periphery** (399 lines): `forceApproveMax` heuristic; referral-fee math; residual-token sweep under/overflow; stealable leftover allowance/balance.

**Tier 3 — Low/Info-leaning**
8. **Signature handling** (`EcrecoverRatifier`/`EcrecoverAuthorizer`/`HashLib`): raw `ecrecover`, no s-malleability check (likely low impact — nonce/root keyed); EIP-712 domain separators; Merkle leaf-index/second-preimage.
9. **Market-id / SSTORE2** (`IdLib`): `INITIAL_CHAIN_ID` post-hardfork clashes; params-as-bytecode round-trip.
10. **Admin/fee setters** (~211-336): `claimContinuousFee` underflow vs slashing race; single-step role transfers (Info).

## Realistic Assessment

Thick, hard contest — not a soft target. 2,157 findings with ~5 days left; shallow surface is saturated. EV for a newcomer realistically lands in the **$150k Medium tier or $20k Low/Info pool** unless you land a genuine High.

**Where un-found bugs most plausibly remain:** the freshly-rewritten `maxRepaid`/RCF liquidation math (commit #944), multi-collateral liquidation precision, bad-debt-socialization when `lossFactor → type(uint128).max`, and cross-function reentrancy outside the seller-take case.

**Bottom line:** enterable with solid Solidity, but treat as a deep-math, POC-mandatory contest. Pick **one** Tier-1 area (best ROI: the new `maxRepaid`/RCF math), build a Foundry POC on `test/BaseTest.sol`, aim for one well-proven Medium/High over volume.
