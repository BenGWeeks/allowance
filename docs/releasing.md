# Preparing an Allowance release

The tag workflow runs the regression, database, archive installation and quality
checks before creating a **draft** GitHub release. It does not publish the release
or submit changes to the upstream LNbits registry.

1. Merge the reviewed changes and choose a new, unused stable version.
2. Update `config.json` to that version. Keep the existing entries and hashes in
   `extensions.json` unchanged: they describe already published archives.
3. After CI passes, create and push the matching `vX.Y.Z` tag. The workflow rejects
   a tag that differs from the version in `config.json`.
4. Review the draft's notes, ZIP, `SHA256SUMS` and `release-manifest.json`. Publish
   only after approving the release. Existing releases are never overwritten by
   the workflow; resolve a failed or partial draft manually before retrying.
5. Add the entry from `release-manifest.json` to `extensions.json` in a reviewed
   follow-up PR. Its hash describes the exact uploaded ZIP, not GitHub's generated
   source archive. The custom manifest feed continues to use `extensions.json`.
6. Submit the repository manifest to the LNbits registry separately, following
   [the registry guide](https://docs.lnbits.com/dev/extensions/registry).
   `manifest.json` contains the repository discovery entry; `config.json` contains
   the extension metadata.

For a local preview of a **committed** tree:

```sh
python3 scripts/build_release.py --repository BenGWeeks/allowance --output /tmp/allowance-release
bash tests/run_release_tests.sh
```

The preview keeps the committed version; it must not replace an existing release.
Uncommitted changes are not included by `git archive`. `.gitattributes` excludes
CI, test fixtures, development tooling and documentation other than the README,
license and extension descriptions from installation archives.

The installation check downloads the published v1.0.6 archive and verifies its
pinned SHA256. It then uses LNbits' native installer, core migration runner and
extension version tracking in disposable containers for fresh installation,
upgrade and reinstallation on both SQLite and PostgreSQL. Upgrade fixtures are
inactive, synthetic records, including a pending payment identity; the check
verifies that their data and schedule survive. Containers use FakeWallet and have
no external network access (PostgreSQL uses an internal Docker network).

These checks cover archive loading and schema upgrades, not real Lightning
settlement, production backups, or acceptance by LNbits maintainers. This remains
a native Python extension; packaging changes do not port it to the WASM permission
framework.
