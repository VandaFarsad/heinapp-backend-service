FROM python:3.14-slim AS base
COPY --from=ghcr.io/astral-sh/uv:0.10.4 /uv /uvx /bin/
WORKDIR /code
ENV APPLICATION_PORT=8000
ENV UV_LINK_MODE=copy
RUN apt update && apt install -y \
    gcc make git iputils-ping libexempi8 g++ libldap2-dev libsasl2-dev ldap-utils libpq-dev vim
COPY uv.lock pyproject.toml ./
RUN uv export --no-dev | uv pip install --system --requirements=-
COPY . .

FROM base AS local
RUN uv export --only-group=dev | uv pip install --system --requirements=-

FROM base AS deploy
RUN uv export --only-group=prod | uv pip install --system --requirements=-
ENTRYPOINT ["bash", "/code/docker-entrypoint.sh"]
