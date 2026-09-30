# Public research snapshot

This repository publishes the research code and results of an independent hobby project. The original local workspace was preserved; this is a curated public copy.

## Included

Research source code, tests, configuration templates, original experiment documents, decision/outcome ledgers, anonymized stimuli, numerical analyses, sampled minute paths, plots, interactive HTML reports and audit summaries. Negative results and the latest failed confirmation are retained.

## Excluded or sanitized

Credentials and environment files; virtual environments and caches; downloaded full market archives; CLI/session transcripts, service diagnostics, collection logs and private working directories; account-specific operational handoff and budget state. Parsed research decisions and their short rationales are retained.

Machine paths are normalized and local thread/session identifiers are removed from structured records. `PUBLICATION_MANIFEST.json` records both the original and exported SHA-256 digest of each copied artifact. Original audit hashes refer to original local files and may not match sanitized public files. The public export does not permit replaying the private runtime-isolation audit; it does permit numerical verification from the included research ledgers and paths.

Some historical scripts refer to excluded local operational files or a specific desktop runner. They are retained as implementation history, not promised as portable commands. Use `scripts/reproduce_published_results.py` for the supported offline numerical reproduction. Collecting new AI opinions requires configuring an appropriate model runner and new, isolated inputs; the offline reproduction does not do that.

## Market-data provenance

The intraday retrieval code uses Binance USDT-M futures candles from `data.binance.vision` and the public futures API. Daily retrieval supports Yahoo Finance, Stooq and Binance. Details are in `src/nai/intraday.py` and `src/nai/data.py`.

The complete downloaded archives are excluded. Acquisition scripts are included so researchers can obtain data from the original sources under the providers' applicable terms. The publication does not assert a redistribution license for those providers' datasets. Included trade-level observations and sampled paths document the reported analyses. No repository-wide code or data license has been added by this publication.

## Reproduction scope

The latest saved native paths cover 180 model-query windows: 60 screening cases and 120 short-hypothesis confirmation cases. The offline script verifies entry/exit returns and reruns the frozen statistics, preserving separate stages. Re-fetching current provider archives may produce data revisions, so it is a different exercise from replaying these saved observations.

The historical query windows are fresh relative to the experiment's listed target exposures, not necessarily unknown prices or independent market regimes. The exclusion convention permits endpoint adjacency; input histories can overlap prior observations. None of the completed work establishes a reliable AI-dependent trading strategy.
