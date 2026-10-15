# Dev container for S3Wear apps and faces: clang + lld (wasm32), Rust with wasm32-unknown-unknown, the s3w CLI and
# the Linux simulator. Build from the repository root:
#
#   docker build -f docker/Dockerfile -t s3w-sdk .
#   docker run --rm -v "$PWD:/work" -w /work s3w-sdk s3w build my-app
#   docker run --rm -v "$PWD:/work" -w /work s3w-sdk s3w run-sim my-app --screenshot out.png
#
# The simulator is headless in the container (no window): use --screenshot and/or --script. The store's check job
# runs in this same image, so "passes here" means "passes in the store".
#
# Build args:
#   WITH_SIM=1       install the simulator with `s3w sim install` (needs a published simulator); 0 leaves it out
#   SIM_VERSION=     a simulator version (default: the latest)
#   RUST_VERSION     the Rust toolchain
#   VERSION          the SDK version, for the image label
FROM ubuntu:24.04

ARG WITH_SIM=1
ARG SIM_VERSION=
ARG RUST_VERSION=1.94.1
ARG VERSION=dev

LABEL org.opencontainers.image.title="s3w-sdk" \
      org.opencontainers.image.description="S3Wear app and face toolchain: clang/lld wasm32, Rust, s3w CLI, simulator" \
      org.opencontainers.image.source="https://github.com/asmsaifs/S3Wear-SDK" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.version="${VERSION}"

ENV DEBIAN_FRONTEND=noninteractive \
    S3W_HOME=/opt/s3w \
    RUSTUP_HOME=/opt/rust/rustup \
    CARGO_HOME=/opt/rust/cargo \
    PATH=/opt/s3w/venv/bin:/opt/rust/cargo/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# gcc + libc: cargo links build scripts for the host even when the target is wasm.
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl clang lld gcc libc6-dev make git zip unzip \
        python3 python3-venv python3-pip \
 && rm -rf /var/lib/apt/lists/* \
 && clang --version | head -1 \
 && clang --print-targets | grep -q wasm32 \
 && wasm-ld --version

RUN curl -fsSL https://sh.rustup.rs | sh -s -- -y --profile minimal --default-toolchain "${RUST_VERSION}" \
        --target wasm32-unknown-unknown --no-modify-path \
 && chmod -R a+rwX /opt/rust \
 && rustc --version

# The CLI as `pip install s3w` would give it: the wheel carries include/, templates/ and rust/.
COPY cli /src/cli
COPY include /src/include
COPY templates /src/templates
COPY rust /src/rust
RUN /src/cli/vendor_sdk.sh \
 && python3 -m venv /opt/s3w/venv \
 && /opt/s3w/venv/bin/pip install --no-cache-dir /src/cli \
 && rm -rf /src

RUN if [ "${WITH_SIM}" = "1" ]; then s3w sim install ${SIM_VERSION:+--version "${SIM_VERSION}"}; fi \
 && chmod -R a+rX /opt/s3w

WORKDIR /work
CMD ["bash"]
