# ==================================== BASE ====================================
ARG INSTALL_PYTHON_VERSION=${INSTALL_PYTHON_VERSION:-3.7}
FROM python:${INSTALL_PYTHON_VERSION}-slim-stretch AS base

RUN apt-get update
RUN apt-get install -y \
    curl

WORKDIR /app
COPY requirements requirements

# ================================= DEVELOPMENT ================================
FROM base AS development
RUN pip install -r requirements/dev.txt
EXPOSE 5000

# ================================= PRODUCTION =================================
FROM base AS production
RUN pip install -r requirements/prod.txt
COPY supervisord.conf /etc/supervisor/supervisord.conf
COPY supervisord_programs /etc/supervisor/conf.d
EXPOSE 5000
ENTRYPOINT ["flask"]
CMD ["run"]

# =================================== MANAGE ===================================
FROM base AS manage
RUN pip install -r requirements/dev.txt
ENTRYPOINT [ "flask" ]
