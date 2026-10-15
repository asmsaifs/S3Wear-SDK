# Install the SDK

## The tools

| For | Install |
|---|---|
| The CLI | Python 3.9 or newer, then `pipx install s3w` (or `pip install s3w`) |
| C apps | A clang with the wasm32 target: `brew install llvm` on macOS, `apt install clang lld` on Linux, or [wasi-sdk](https://github.com/WebAssembly/wasi-sdk). `CLANG=/path/to/clang` picks one |
| Rust apps | [rustup](https://rustup.rs), then `rustup target add wasm32-unknown-unknown` |
| The simulator | `s3w sim install` (macOS and Linux x86_64). On Windows use WSL2 |
| Installing on a watch | The CLI installs `pyserial` for you |

Check the CLI works:

```bash
s3w --help
s3w sim install        # downloads the simulator, checks its signature, keeps it in ~/.s3w/sim
s3w new demo && s3w run-sim demo
```

`s3w sim install` verifies the download against the release key before it unpacks anything. `s3w sim update` fetches
a newer simulator, `s3w sim list` shows what is installed. If you build the simulator yourself, set `S3W_SIM` to it.

The simulator and the watch must agree on the API: `s3w run-sim` warns when your app asks for a higher `api_level`
than the simulator runs (`s3w sim update` fixes that).

## The dev container

If you would rather install nothing, the SDK ships a container with clang, Rust, the CLI and the simulator:

```bash
docker run --rm -v "$PWD:/work" -w /work ghcr.io/asmsaifs/s3w-sdk:latest s3w build my-app
docker run --rm -v "$PWD:/work" -w /work ghcr.io/asmsaifs/s3w-sdk:latest s3w run-sim my-app --screenshot out.png
```

The simulator is headless in the container: use `--screenshot` and `--script` ([simulator scripts](../reference/simulator-scripts.md)),
not a window. The store checks your submission in this same image, so passing there means passing in the store.

## Where files go

| Path | What |
|---|---|
| `~/.s3w/sim/<version>/` | Installed simulators (`$S3W_HOME` moves `~/.s3w`) |
| `~/.s3w/dev.key` | Your signing key, made by `s3w keygen` |
| `<app>/build/` | Build output: `app.wasm` and `<id>.s3app` |
