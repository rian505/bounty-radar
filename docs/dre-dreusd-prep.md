# DRE App — dreUSD — Attack Surface Prep (Sherlock contest #1259)

> Prepared 2026-06-08, BEFORE code drop. Contest opens **2026-06-08 15:00 UTC**,
> closes **2026-06-17 15:00 UTC**. Pool: $60k USDC. Scope: dreUSD core only.
> Repo drops at start — clone it, then work this list top-down.

## Scope (from Sherlock description)
- `dreUSD` — ERC-20 token
- `dreUSDs` — ERC-4626 vault
- on-chain **mint** / **redemption** logic
- **rewards distribution** logic
- **LayerZero OFT** adapters (cross-chain)

Backing: USDC 1:1 + real-estate credit + short-duration secured loans (off-chain RWA → oracle/admin trust surface).

## Priority attack classes (work in this order — highest EV first)

### 1. ERC-4626 inflation / first-depositor attack (HIGHEST EV)
The single most common 4626 finding. Check:
- [ ] Is the vault vulnerable to the classic donation/inflation attack? First depositor mints 1 share, donates assets directly to vault, second depositor's deposit rounds to 0 shares.
- [ ] Are virtual shares / dead shares / initial mint used as mitigation? If NOT → likely valid.
- [ ] `convertToShares` / `convertToAssets` rounding direction — does any path round in the user's favor on both deposit AND withdraw (value extraction)?
- [ ] `previewDeposit` vs actual `deposit` mismatch.

### 2. Mint / redeem accounting (stablecoin core)
- [ ] dreUSD minted 1:1 with USDC — is the ratio enforced on BOTH mint and redeem, or can rounding/fee asymmetry let you redeem more than you minted?
- [ ] Decimals: USDC is 6 decimals, dreUSD likely 18. Any unscaled arithmetic = catastrophic. Grep for `* 1e12`, `/ 1e12`, decimal conversions.
- [ ] Redemption when backed by illiquid RWA — can you redeem during a state where vault lacks USDC? Forced loss socialization?
- [ ] Pause/blacklist during redeem — griefing or fund lock?

### 3. Rewards distribution
- [ ] Can rewards be claimed multiple times (no claimed-flag / checkpoint reset)?
- [ ] Reward = f(balance) read at claim time → flash-loan / deposit-right-before-snapshot inflation?
- [ ] Rounding dust accumulation drainable?
- [ ] Reward token == underlying? Then deposits and rewards share an accounting pool — confusion bug.

### 4. LayerZero OFT cross-chain (high severity if found)
- [ ] OFT `_debit`/`_credit` — does burned-on-source exactly equal minted-on-dest? Decimal/dust truncation (`sharedDecimals` vs `localDecimals`) = mint/burn mismatch.
- [ ] Can a message be replayed / double-delivered to mint twice?
- [ ] Peer trust: is `setPeer` access-controlled? Untrusted peer = infinite mint.
- [ ] Rate-limit / supply cap respected cross-chain or only local?
- [ ] Slippage/`minAmount` on receive — can it revert and trap funds in-flight?

### 5. Oracle / RWA backing trust
- [ ] How is the off-chain backing value brought on-chain? Single admin setter = centralization (often Sherlock-valid as it affects redemption price).
- [ ] Stale price usage on redeem?

## Mechanical first-pass (run immediately on clone)
```bash
# from m11 quick scan, tuned for this protocol
grep -rn "convertToShares\|convertToAssets\|previewDeposit\|previewRedeem" src/
grep -rn "1e12\|10\*\*12\|decimals()" src/        # decimal mismatch USDC(6)/dreUSD(18)
grep -rn "_debit\|_credit\|sharedDecimals\|setPeer" src/   # OFT
grep -rn "block.timestamp\|onlyOwner\|onlyRole" src/
grep -rn "mint(\|burn(\|_mint\|_burn" src/
# count scope size
find src -name '*.sol' | xargs wc -l | tail -1
```

## Submission discipline (Sherlock)
- Sherlock judges duplicates hard — a finding shared by N people splits the reward. Novelty matters.
- Mandatory: clear PoC / reasoning, exact severity (High/Medium), affected `file:line`.
- Don't submit theoretical — show the value-extraction path or fund-loss scenario.
- Watch the escalation window after judging.

## Honest EV note
$60k pool is split across ALL valid findings + Lead/Junior Watson weighting. A single Medium dup might net $50–500. A unique High could net several $k. Realistic, not a jackpot. The win condition is a NOVEL finding the audit firm missed — possible because contest code is often freshly written (this is `is_judging_v3`, looks new).
