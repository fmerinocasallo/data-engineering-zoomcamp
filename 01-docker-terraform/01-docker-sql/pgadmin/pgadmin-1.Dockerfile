FROM dpage/pgadmin4:latest

USER root
RUN mkdir /certs \
    && chown pgadmin:root /certs
USER pgadmin

ENTRYPOINT ["/entrypoint.sh"]