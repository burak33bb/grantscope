# grantscope

GrantScope is a GenLayer project submission checklist app.

It records whether a submission has the basic evidence links reviewers need:
GitHub repository, GenLayer explorer contract, live app URL, and optional demo.

Scope: this contract checks link presence and format only. It does not fetch,
authenticate, or verify the external contents of those links.

## contract

`contracts/grantscope_verifier.py`

The contract stores the latest checklist result onchain with:

- category
- project name
- proof score
- submitted evidence URLs
- deterministic result such as `EVIDENCE_READY` or `NEEDS_MORE_EVIDENCE`

## app

The frontend connects a wallet, submits the checklist transaction to GenLayer,
waits for finalization, then reads the stored checklist report from the contract.
