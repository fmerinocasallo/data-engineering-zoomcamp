FROM dpage/pgadmin4:latest

USER pgadmin
RUN mkdir -p /var/lib/pgadmin/storage/${PGADMIN_USER_CONFIG_DIR}/.postgresql \
    && chown pgadmin:root /var/lib/pgadmin/storage/${PGADMIN_USER_CONFIG_DIR}/.postgresql

ENTRYPOINT ["/entrypoint.sh"]