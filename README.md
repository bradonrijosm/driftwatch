# driftwatch

A small daemon that monitors local config files against a remote source of truth and alerts on drift.

---

## Installation

```bash
pip install driftwatch
```

Or install from source:

```bash
git clone https://github.com/yourorg/driftwatch.git && cd driftwatch && pip install .
```

---

## Usage

Create a configuration file (`driftwatch.yml`) to define what to watch:

```yaml
remote: https://config.example.com/truth/app.yml
local: /etc/myapp/config.yml
interval: 60
alert:
  slack_webhook: https://hooks.slack.com/services/xxx/yyy/zzz
```

Then start the daemon:

```bash
driftwatch --config driftwatch.yml
```

driftwatch will poll the remote source every `interval` seconds and compare it against the local file. If a difference is detected, an alert is sent to the configured channel.

**One-shot check (no daemon):**

```bash
driftwatch --config driftwatch.yml --once
```

---

## Options

| Flag | Description |
|------|-------------|
| `--config` | Path to the driftwatch config file |
| `--once` | Run a single check and exit |
| `--verbose` | Enable detailed diff output |

---

## License

MIT © yourorg