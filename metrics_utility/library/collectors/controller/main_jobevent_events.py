"""Keyset-paginated extractor for ``main_jobevent`` records from the Controller database.

Uses LATERAL JSONB cast to extract ``event_data`` fields at the DB level.
Requires explicit ``job_created`` bounds to enable partition pruning on the
hourly-partitioned ``main_jobevent`` table.
"""

import time


# Event types used in analysis — mirrors main_jobevent_service.py
_RELEVANT_EVENTS = (
    'runner_on_ok',
    'runner_on_async_ok',
    'runner_item_on_ok',
    'runner_on_failed',
    'runner_on_async_failed',
    'runner_item_on_failed',
    'runner_on_unreachable',
    'runner_item_on_unreachable',
    'runner_on_skipped',
    'runner_item_on_skipped',
    'warning',
    'deprecated',
)

_EVENT_TYPES_SQL = ', '.join(f"'{e}'" for e in _RELEVANT_EVENTS)

_SELECT = """
    SELECT
        e.id,
        e.created,
        e.modified,
        e.job_created,
        e.uuid,
        e.parent_uuid,
        e.event,
        (ed.event_data->>'task_action')                           AS task_action,
        (ed.event_data->>'resolved_action')                       AS resolved_action,
        (ed.event_data->>'resolved_role')                         AS resolved_role,
        (ed.event_data->>'duration')                              AS duration,
        (ed.event_data->>'start')::timestamptz                    AS start,
        (ed.event_data->>'end')::timestamptz                      AS end,
        (ed.event_data->>'task_uuid')                             AS task_uuid,
        COALESCE((ed.event_data->>'ignore_errors')::boolean, false) AS ignore_errors,
        e.failed,
        e.changed,
        e.playbook,
        e.play,
        e.task,
        e.role,
        e.job_id                                                  AS job_remote_id,
        e.job_id,
        e.host_id                                                 AS host_remote_id,
        e.host_id,
        e.host_name,
        ed.event_data->'res'->'warnings'                          AS warnings,
        ed.event_data->'res'->'deprecations'                      AS deprecations
    FROM main_jobevent e
    CROSS JOIN LATERAL (
        SELECT replace(e.event_data, '\\u', '\\u005cu')::jsonb AS event_data
    ) AS ed
"""


class JobEventExtractor:
    """Stream ``main_jobevent`` rows in batches using keyset pagination.

    Partition-aware: literal timestamp values in the WHERE clause allow
    PostgreSQL to prune hourly partitions, matching the approach used in
    ``main_jobevent_service.py``.

    Each call to :meth:`__iter__` yields one batch (list of dicts) of up to
    :attr:`batch_size` rows ordered by ``(job_created ASC, id ASC)``.

    Args:
        db: psycopg3-compatible connection (``db.cursor()`` context manager).
        since: Inclusive lower bound on ``job_created`` (timezone-aware datetime).
        until: Exclusive upper bound on ``job_created`` (timezone-aware datetime).
        batch_size: Rows per page (default 10 000).
        throttle_seconds: Sleep between full pages to protect the source DB (default 0.1).
    """

    def __init__(self, db, *, since=None, until=None, batch_size=10_000, throttle_seconds=0.1):
        self.db = db
        self.since = since
        self.until = until
        self.batch_size = batch_size
        self.throttle_seconds = throttle_seconds

    def _build_query(self, cursor_job_created, cursor_id):
        """Assemble the paginated SELECT with literal timestamps for partition pruning."""
        conditions = [f'e.event IN ({_EVENT_TYPES_SQL})']

        # Literal timestamps so the planner sees them and can prune partitions.
        # This follows the same pattern as main_jobevent_service.py.
        if self.since is not None:
            conditions.append(f"e.job_created >= '{self.since.isoformat()}'::timestamptz")
        if self.until is not None:
            conditions.append(f"e.job_created < '{self.until.isoformat()}'::timestamptz")

        # Keyset continuation: skip rows we have already seen
        if cursor_job_created is not None:
            conditions.append(f"(e.job_created, e.id) > ('{cursor_job_created.isoformat()}'::timestamptz, {cursor_id})")

        where = ' AND '.join(conditions)
        return f'{_SELECT} WHERE {where} ORDER BY e.job_created ASC, e.id ASC LIMIT {self.batch_size}'

    def __iter__(self):
        """Yield batches of event row dicts, advancing the keyset cursor after each page.

        Yields:
            list[dict]: One batch of up to :attr:`batch_size` row dicts.
        """
        cursor_job_created = None
        cursor_id = None
        first_page = True

        with self.db.cursor() as cur:
            while True:
                if not first_page and self.throttle_seconds > 0:
                    time.sleep(self.throttle_seconds)
                first_page = False

                cur.execute(self._build_query(cursor_job_created, cursor_id))
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchmany(self.batch_size)

                if not rows:
                    break

                batch = [dict(zip(columns, row)) for row in rows]
                yield batch

                last = batch[-1]
                cursor_job_created = last['job_created']
                cursor_id = last['id']

                if len(batch) < self.batch_size:
                    break
