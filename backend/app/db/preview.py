"""DEV-only PR connection policy; never derive database scope from HTTP input."""

import os
import re

from sqlalchemy import event
from sqlalchemy.engine import make_url


def preview_schema(env=None):
    env = os.environ if env is None else env
    if env.get('IS_PULL_REQUEST') != 'true':
        return None
    hostname = env.get('RENDER_EXTERNAL_HOSTNAME', '')
    # The separate production service's previews never run DEV bootstrap.
    if re.fullmatch(r'jobshield-backend-pr-[1-9][0-9]{0,9}\.onrender\.com', hostname):
        return None
    match = re.fullmatch(r'jobshield-pr-([1-9][0-9]{0,9})\.onrender\.com', hostname)
    if not match:
        raise ValueError('Invalid DEV PR hostname; refusing database scope.')
    return 'preview_pr_' + match[1]


def validate_preview_database(raw_url):
    try:
        url = make_url(raw_url)
        valid = (
            url.drivername == 'postgresql+psycopg'
            and url.host == 'aws-0-ap-southeast-1.pooler.supabase.com'
            and url.port == 5432 and url.database == 'postgres'
            and url.username == 'postgres.vleyapvlgnukcawgxozg'
            and not (set(url.query) - {'sslmode'})
            and url.query.get('sslmode', 'require') in {'require', 'verify-ca', 'verify-full'}
        )
    except Exception:
        valid = False
    if not valid:
        raise ValueError('Database is not the approved DEV session connection.')
    return url.update_query_dict({'sslmode': url.query.get('sslmode', 'require')})


def scope_engine(engine, schema):
    if not re.fullmatch(r'preview_pr_[1-9][0-9]{0,9}', schema):
        raise ValueError('Invalid PR schema.')

    @event.listens_for(engine, 'checkout')
    def scope_connection(connection, record, proxy):
        # Supavisor ignores startup options; re-apply scope on every lease.
        previous = connection.autocommit
        connection.autocommit = True
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT set_config('search_path', %s, false)", (schema,))
                cursor.execute("SELECT current_setting('search_path')")
                if cursor.fetchone()[0] != schema:
                    raise ValueError('PR database scope could not be verified.')
        finally:
            connection.autocommit = previous
