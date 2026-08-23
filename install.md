# Install DCC-MCP for Adobe Illustrator

This is the canonical installation contract for the Illustrator adapter. The
installer plans first, writes only an adapter-owned CEP extension and receipt,
and reports success only after a real typed Illustrator readiness call.

## Requirements

- Python 3.9 or newer for the adapter process.
- `dcc-mcp-core` 0.19.91 or newer.
- Illustrator 23.0 / CC 2019 or newer.
- An `adobepy` runtime containing the broker executable and built Illustrator
  CEP bridge. The Python wheel alone does not contain that runtime.
- A private `ADOBEPY_TOKEN` set in the environment used by the broker,
  installer, and adapter. Credentials are environment-only and are never
  accepted as a lifecycle CLI argument.

Install the Python package in the exact interpreter that will run the adapter:

```bash
python -m pip install --upgrade dcc-mcp-illustrator
```

## Supported versions and platforms

| Platform | Host integration |
| --- | --- |
| Windows | Supported. Illustrator is discovered under Adobe's Program Files layout; the CEP extension is installed below `%APPDATA%\Adobe\CEP\extensions`. The published `adobepy` install guide currently documents a Windows x64 runtime bundle. |
| macOS | Supported when an operator provides a compatible `adobepy` broker/CLI. Illustrator is discovered in `/Applications`; the CEP extension is installed below `~/Library/Application Support/Adobe/CEP/extensions`. |
| Linux | The Python package can be inspected and tested, but Adobe Illustrator and live CEP integration are unavailable. Install and verify fail closed. |

The bridge manifest supports Illustrator host ID `ILST` from version 23.0.
Local unsigned CEP development extensions may require Adobe's user-scoped
`PlayerDebugMode` setting for the matching CSXS runtime. The installer does not
silently weaken that host-wide policy; when the CEP session is absent it emits
one exact machine-executable next step and continues to report
`directly_usable: false`.

## Agent quick path

Set the runtime executable and one private token in the current environment.
Examples:

```powershell
$env:ADOBEPY_CLI = 'C:\Tools\adobepy\bin\adobepy.exe'
$env:ADOBEPY_TOKEN = Read-Host 'Local broker token'
$hostPath = 'C:\Program Files\Adobe\Adobe Illustrator 2025\Support Files\Contents\Windows\Illustrator.exe'
dcc-mcp-illustrator install --json --dry-run --dcc-path $hostPath --python (Get-Command python).Source
dcc-mcp-illustrator install --json --yes --dcc-path $hostPath --python (Get-Command python).Source
```

```bash
export ADOBEPY_CLI="$HOME/Tools/adobepy/bin/adobepy"
read -rs ADOBEPY_TOKEN && export ADOBEPY_TOKEN
dcc-mcp-illustrator install --json --dry-run \
  --dcc-path "/Applications/Adobe Illustrator 2025/Adobe Illustrator.app/Contents/MacOS/Adobe Illustrator" \
  --python "$(command -v python3)"
dcc-mcp-illustrator install --json --yes \
  --dcc-path "/Applications/Adobe Illustrator 2025/Adobe Illustrator.app/Contents/MacOS/Adobe Illustrator" \
  --python "$(command -v python3)"
```

Planning and `--dry-run` never create the CEP target, staging directory, or
receipt. Applying repeats all safety-sensitive preflight checks. If the bridge
is staged but Illustrator is not connected, the command exits 40 and provides
one `next_steps[]` entry; file copying alone is not reported as installation
success.

## Manual path

The supported manual path still uses the canonical lifecycle so staging,
rollback, secret redaction, and receipts cannot be bypassed:

1. Install the Python wheel into the selected adapter interpreter.
2. Obtain a supported `adobepy` runtime from its verified release bundle or an
   audited source build; do not scrape an unpinned latest binary.
3. Set `ADOBEPY_CLI`, `ADOBEPY_TOKEN`, and optionally
   `ADOBEPY_BROKER_URL` in the environment.
4. Run the dry-run command and inspect `plan.host`, `plan.python`,
   `plan.bridge`, and `installed_state`.
5. Re-run with `--yes`.
6. Execute the single returned host-enablement step if present, then restart or
   activate Illustrator so the manifest's CEP `StartOn` event can connect.
7. Run `dcc-mcp-illustrator verify --json`.

The installer writes a receipt under
`~/.dcc-mcp/illustrator/receipts/illustrator.json`. It records paths, versions,
and non-sensitive file digests. The secret-bearing `adobepy.config.js` is marked
sensitive and its contents are never copied into JSON, logs, or the receipt.

## Verify

```bash
dcc-mcp-illustrator status --json
dcc-mcp-illustrator verify --json
```

Verification is ordered and fail-closed:

1. validate the receipt, expected CEP path, files, and digests;
2. import this adapter and `adobe.illustrator.Illustrator` in the receipted
   Python interpreter;
3. query the `adobepy` broker health endpoint;
4. require a connected Illustrator CEP session;
5. call the existing typed Illustrator readiness probe, including the real host
   version RPC.

Only all five passing produces `directly_usable: true`. This repository's CI
uses a synthetic CEP profile and injected typed probes; it does not claim a
live Illustrator host on GitHub runners.

## Upgrade

```bash
python -m pip install --upgrade dcc-mcp-illustrator
dcc-mcp-illustrator upgrade --json --dry-run
dcc-mcp-illustrator upgrade --json --yes
```

Upgrade consumes the existing receipt, stages a complete new CEP tree, and
atomically swaps it. A failed commit restores the previous tree and preserves
the prior receipt. A damaged but valid receipted install is reported as
`repair`; an unreceipted CEP directory is `partial` and is never overwritten.

## Uninstall

```bash
dcc-mcp-illustrator uninstall --json --dry-run
dcc-mcp-illustrator uninstall --json --yes
python -m pip uninstall dcc-mcp-illustrator
```

Uninstall removes only the exact CEP directory bound by a valid receipt. It is
idempotent when that state is already absent. Ambiguous, unreceipted files are
left untouched. A proven Windows file lock returns exit 50 and requires an
Illustrator restart before retrying.

## Troubleshooting

### Exit 10: host, interpreter, policy, or partial state

Inspect the JSON `verify.failure_stage`. Supply the exact Illustrator executable
with `--dcc-path`, the adapter interpreter with `--python`, and repair only a
valid receipted state. Move an unowned CEP directory aside yourself after
confirming its ownership; the installer will not delete it.

### Exit 20: `adobepy` runtime unavailable

The PyPI SDK wheel does not ship the broker/bridge CLI. Point `ADOBEPY_CLI` to a
verified runtime executable. macOS currently requires an operator-provided
compatible runtime; no adapter cache or unpinned binary download is used.

### Exit 40: broker, CEP session, or typed RPC unavailable

Start the broker with the same environment token, execute the returned CEP
enablement step if needed, and restart or activate Illustrator. Then rerun
`dcc-mcp-illustrator verify --json`. A reachable port is insufficient: the CEP
session and typed Illustrator RPC must both pass.

### Exit 50: locked files

Close Illustrator and retry the same command. Exit 50 is reserved for a proven
loaded or locked artifact; an ordinary closed host or failed readiness probe
returns exit 40.

### Bootstrap failure

Read `~/.dcc-mcp/illustrator/bootstrap-errors.json`. The rolling diagnostic is
bounded and redacts configured tokens and URL user information. Resolve the
reported stage, then rerun status and verify.

For the underlying runtime bundle and CEP source workflow, see the
[`adobepy` installation guide](https://github.com/dcc-mcp/adobepy/blob/main/install.md).
