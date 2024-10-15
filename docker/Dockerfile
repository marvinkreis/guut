FROM ghcr.io/astral-sh/uv:bookworm

RUN --mount=type=cache,sharing=locked,target=/var/lib/apt/lists \
    --mount=type=cache,sharing=locked,target=/var/cache/apt \
    apt-get update -y && apt-get install clang -y

WORKDIR /guut

COPY guut /guut/guut
COPY docker/run_internal.sh /guut/run.sh

RUN --mount=type=cache,sharing=locked,target=/root/.cache/uv \
    --mount=type=bind,readonly,source=uv.lock,target=uv.lock \
    --mount=type=bind,readonly,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-editable --no-dev --no-install-project

ENTRYPOINT [ "bash" ]
