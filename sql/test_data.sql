--
-- Test Data Generation Script for metrics-utility
--
-- Purpose: Generate medium-scale test data (100s-1000s of records) for development and testing
-- Assumes: Database schema already exists (run latest.sql first)
-- Usage: psql -U awx -h localhost -d awx < sql/test_data.sql
--
-- This script generates realistic test data across all tables used by metrics-utility collectors
-- All generated data uses 'testdata' suffix for easy identification and cleanup
--

-- Helper function: Create partition for main_jobevent if it doesn't exist
CREATE OR REPLACE FUNCTION ensure_jobevent_partition(ts TIMESTAMP WITH TIME ZONE)
RETURNS TEXT AS $$
DECLARE
  partition_date TEXT;
  partition_hour TEXT;
  partition_name TEXT;
  start_time TIMESTAMP WITH TIME ZONE;
  end_time TIMESTAMP WITH TIME ZONE;
BEGIN
  partition_date := to_char(ts, 'YYYYMMDD');
  partition_hour := to_char(ts, 'HH24');
  partition_name := 'main_jobevent_' || partition_date || '_' || partition_hour;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = partition_name
  ) THEN
    start_time := date_trunc('hour', ts);
    end_time := start_time + interval '1 hour';

    EXECUTE format('CREATE TABLE public.%I (LIKE public.main_jobevent INCLUDING DEFAULTS INCLUDING CONSTRAINTS)', partition_name);
    EXECUTE format('ALTER TABLE public.main_jobevent ATTACH PARTITION public.%I FOR VALUES FROM (%L) TO (%L)',
                   partition_name, start_time, end_time);

    RAISE NOTICE '  Created partition: %', partition_name;
  END IF;

  RETURN partition_name;
END;
$$ LANGUAGE plpgsql;

-- Helper function: Generate random IP address
CREATE OR REPLACE FUNCTION random_ip()
RETURNS TEXT AS $$
BEGIN
  RETURN (floor(random()*256)::int)::text || '.' ||
         (floor(random()*256)::int)::text || '.' ||
         (floor(random()*256)::int)::text || '.' ||
         (floor(random()*256)::int)::text;
END;
$$ LANGUAGE plpgsql;

-- Helper function: Generate random timestamp within a day
CREATE OR REPLACE FUNCTION random_timestamp_in_day(base_ts TIMESTAMP WITH TIME ZONE)
RETURNS TIMESTAMP WITH TIME ZONE AS $$
BEGIN
  RETURN base_ts + (random() * interval '1 day');
END;
$$ LANGUAGE plpgsql;

-- Helper function: Weighted random job status
CREATE OR REPLACE FUNCTION random_job_status()
RETURNS TEXT AS $$
DECLARE
  rand FLOAT;
BEGIN
  rand := random();
  IF rand < 0.70 THEN RETURN 'successful';
  ELSIF rand < 0.85 THEN RETURN 'failed';
  ELSIF rand < 0.95 THEN RETURN 'running';
  ELSE RETURN 'pending';
  END IF;
END;
$$ LANGUAGE plpgsql;

-- Main data generation block
DO $$
DECLARE
  -- ========================================
  -- CONFIGURABLE PARAMETERS
  -- ========================================
  num_organizations INTEGER := 5;            -- Number of organizations (5-10)
  inventories_per_org INTEGER := 3;          -- Inventories per org (2-5)
  hosts_per_inventory INTEGER := 30;         -- Hosts per inventory (20-50)
  jobs_per_day INTEGER := 15;                -- Jobs per day (10-20)
  events_per_job_host INTEGER := 8;          -- Events per job-host pair (5-15)
  days_to_generate INTEGER := 7;             -- Days of historical data (1-30)
  hosts_per_job INTEGER := 7;                -- Average hosts per job (5-10)

  -- Time range
  base_date TIMESTAMP WITH TIME ZONE := '2025-06-01 00:00:00+00';

  -- ID tracking arrays
  org_ids INTEGER[] := ARRAY[]::INTEGER[];
  inventory_ids INTEGER[] := ARRAY[]::INTEGER[];
  host_ids INTEGER[] := ARRAY[]::INTEGER[];
  instance_uuids UUID[] := ARRAY[]::UUID[];
  ee_ids INTEGER[] := ARRAY[]::INTEGER[];
  ujt_ids INTEGER[] := ARRAY[]::INTEGER[];
  job_ids INTEGER[] := ARRAY[]::INTEGER[];

  -- Temporary variables
  org_id INTEGER;
  inv_id INTEGER;
  host_id INTEGER;
  instance_id INTEGER;
  instance_uuid UUID;
  ee_id INTEGER;
  ujt_id INTEGER;
  uj_id INTEGER;
  job_id INTEGER;
  jhs_id INTEGER;
  content_type_id INTEGER;

  -- Loop counters
  i INTEGER;
  j INTEGER;
  k INTEGER;
  m INTEGER;
  day_offset INTEGER;
  hour_offset INTEGER;

  -- Naming and data generation
  random_suffix TEXT := 'testdata';
  host_name TEXT;
  job_name TEXT;
  job_status TEXT;
  job_created TIMESTAMP WITH TIME ZONE;
  job_started TIMESTAMP WITH TIME ZONE;
  job_finished TIMESTAMP WITH TIME ZONE;
  event_type TEXT;
  event_failed BOOLEAN;
  event_changed BOOLEAN;
  partition_name TEXT;

  -- Hostname type arrays
  host_types TEXT[] := ARRAY['web', 'db', 'app', 'worker', 'cache', 'queue', 'api', 'frontend', 'backend', 'monitor'];
  event_types TEXT[] := ARRAY['runner_on_ok', 'runner_on_failed', 'runner_on_skipped', 'runner_item_on_ok'];
  task_actions TEXT[] := ARRAY['ansible.builtin.setup', 'ansible.builtin.copy', 'ansible.builtin.template', 'ansible.builtin.service', 'ansible.builtin.package', 'ansible.builtin.command'];

  -- Selected hosts for current job
  selected_host_ids INTEGER[];
  selected_host_id INTEGER;

BEGIN
  RAISE NOTICE '========================================';
  RAISE NOTICE 'Test Data Generation Starting';
  RAISE NOTICE '========================================';
  RAISE NOTICE 'Configuration:';
  RAISE NOTICE '  Organizations: %', num_organizations;
  RAISE NOTICE '  Inventories per org: %', inventories_per_org;
  RAISE NOTICE '  Hosts per inventory: %', hosts_per_inventory;
  RAISE NOTICE '  Jobs per day: %', jobs_per_day;
  RAISE NOTICE '  Days to generate: %', days_to_generate;
  RAISE NOTICE '  Events per job-host: %', events_per_job_host;
  RAISE NOTICE '';

  -- ========================================
  -- PHASE 1: Foundation Tables
  -- ========================================
  RAISE NOTICE 'Phase 1/6: Creating foundation tables...';

  -- Get or create content type for 'job' model
  SELECT id INTO content_type_id
  FROM django_content_type
  WHERE app_label = 'main' AND model = 'job';

  IF content_type_id IS NULL THEN
    INSERT INTO django_content_type (app_label, model)
    VALUES ('main', 'job')
    RETURNING id INTO content_type_id;
    RAISE NOTICE '  Created content type for job model (id: %)', content_type_id;
  END IF;

  -- Create organizations
  FOR i IN 1..num_organizations LOOP
    INSERT INTO main_organization (
      created, modified, description, name, max_hosts
    ) VALUES (
      base_date,
      base_date,
      'Test organization ' || i,
      'Org-' || i || '-' || random_suffix,
      0
    )
    RETURNING id INTO org_id;

    org_ids := array_append(org_ids, org_id);
  END LOOP;
  RAISE NOTICE '  Created % organizations', array_length(org_ids, 1);

  -- Create controller instances
  FOR i IN 1..2 LOOP
    instance_uuid := gen_random_uuid();

    INSERT INTO main_instance (
      uuid, hostname, created, modified, capacity, version,
      capacity_adjustment, cpu, memory, cpu_capacity, mem_capacity,
      enabled, managed_by_policy, ip_address, node_type,
      last_seen, errors, last_health_check, node_state,
      health_check_started, managed
    ) VALUES (
      instance_uuid,
      'instance-' || i || '-' || random_suffix,
      base_date,
      base_date,
      100,
      '1.0.0',
      1.00,
      4.0,
      17179869184,  -- 16 GiB
      100,
      16384,        -- MiB
      true,
      false,
      random_ip(),
      'control',
      base_date,
      '',
      base_date,
      'running',
      base_date,
      true
    )
    RETURNING id INTO instance_id;

    instance_uuids := array_append(instance_uuids, instance_uuid);
  END LOOP;
  RAISE NOTICE '  Created % controller instances', array_length(instance_uuids, 1);

  -- Create execution environments
  FOR i IN 1..3 LOOP
    INSERT INTO main_executionenvironment (
      created, modified, name, description, image, organization_id,
      credential_id, pull, managed
    ) VALUES (
      base_date,
      base_date,
      'EE-' || i || '-' || random_suffix,
      'Execution environment ' || i,
      'quay.io/ansible/awx-ee:latest',
      org_ids[1],  -- Link to first org
      NULL,
      '',
      false
    )
    RETURNING id INTO ee_id;

    ee_ids := array_append(ee_ids, ee_id);
  END LOOP;
  RAISE NOTICE '  Created % execution environments', array_length(ee_ids, 1);

  -- ========================================
  -- PHASE 2: Inventories and Hosts
  -- ========================================
  RAISE NOTICE 'Phase 2/6: Creating inventories and hosts...';

  -- Create inventories for each organization
  FOREACH org_id IN ARRAY org_ids LOOP
    FOR i IN 1..inventories_per_org LOOP
      INSERT INTO main_inventory (
        created, modified, description, name, variables,
        has_active_failures, total_hosts, hosts_with_active_failures,
        total_groups, has_inventory_sources, total_inventory_sources,
        inventory_sources_with_failures, organization_id, kind,
        pending_deletion, prevent_instance_group_fallback
      ) VALUES (
        base_date,
        base_date,
        '',
        'Inventory-' || org_id || '-' || i || '-' || random_suffix,
        '{}',
        false,
        hosts_per_inventory,
        0,
        0,
        false,
        0,
        0,
        org_id,
        '',
        false,
        false
      )
      RETURNING id INTO inv_id;

      inventory_ids := array_append(inventory_ids, inv_id);
    END LOOP;
  END LOOP;
  RAISE NOTICE '  Created % inventories', array_length(inventory_ids, 1);

  -- Create hosts for each inventory
  FOREACH inv_id IN ARRAY inventory_ids LOOP
    FOR i IN 1..hosts_per_inventory LOOP
      host_name := host_types[(i % array_length(host_types, 1)) + 1] || '-' ||
                   inv_id || '-' || i || '-' || random_suffix;

      INSERT INTO main_host (
        created, modified, description, name, enabled,
        instance_id, variables, inventory_id, ansible_facts
      ) VALUES (
        base_date,
        base_date,
        '',
        host_name,
        true,
        instance_uuids[1]::text,
        $yaml$ansible_connection: ssh
ansible_user: ansible
ansible_port: 22
ansible_ssh_private_key_file: /home/ansible/.ssh/id_rsa
$yaml$,
        inv_id,
        '{}'::jsonb
      )
      RETURNING id INTO host_id;

      host_ids := array_append(host_ids, host_id);
    END LOOP;
  END LOOP;
  RAISE NOTICE '  Created % hosts', array_length(host_ids, 1);

  -- ========================================
  -- PHASE 3: Job Templates
  -- ========================================
  RAISE NOTICE 'Phase 3/6: Creating job templates...';

  -- Create unified job templates
  FOR i IN 1..5 LOOP
    INSERT INTO main_unifiedjobtemplate (
      created, modified, description, name,
      polymorphic_ctype_id, organization_id,
      last_job_failed, status
    ) VALUES (
      base_date,
      base_date,
      'Test job template ' || i,
      'JobTemplate-' || i || '-' || random_suffix,
      content_type_id,
      org_ids[(i % array_length(org_ids, 1)) + 1],
      false,
      'never updated'
    )
    RETURNING id INTO ujt_id;

    ujt_ids := array_append(ujt_ids, ujt_id);
  END LOOP;
  RAISE NOTICE '  Created % job templates', array_length(ujt_ids, 1);

  -- ========================================
  -- PHASE 4: Jobs and Events (Time-Distributed)
  -- ========================================
  RAISE NOTICE 'Phase 4/6: Generating jobs and events across % days...', days_to_generate;
  RAISE NOTICE '  This may take a while...';

  -- Outer loop: Days
  FOR day_offset IN 0..(days_to_generate - 1) LOOP
    RAISE NOTICE '  Day %/%: Generating % jobs...', day_offset + 1, days_to_generate, jobs_per_day;

    -- Inner loop: Jobs per day
    FOR j IN 1..jobs_per_day LOOP
      -- Calculate job timestamps
      job_created := base_date + (day_offset || ' days')::interval +
                     (random() * interval '24 hours');
      job_started := job_created + (random() * interval '5 minutes');
      job_status := random_job_status();

      IF job_status = 'successful' OR job_status = 'failed' THEN
        job_finished := job_started + (random() * interval '30 minutes');
      ELSE
        job_finished := NULL;  -- Running/pending jobs not finished
      END IF;

      job_name := 'Job-' || day_offset || '-' || j || '-' || random_suffix;

      -- Create unified job
      INSERT INTO main_unifiedjob (
        created, modified, description, name, launch_type,
        cancel_flag, status, failed, started, finished, elapsed,
        unified_job_template_id, polymorphic_ctype_id,
        organization_id, execution_environment_id, execution_node,
        controller_node, job_explanation, instance_group_id,
        ansible_version, job_args, job_cwd, start_args,
        result_traceback, celery_task_id, emitted_events,
        dependencies_processed, installed_collections, task_impact, job_env
      ) VALUES (
        job_created,
        COALESCE(job_finished, job_started),
        '',
        job_name,
        'manual',
        false,
        job_status,
        (job_status = 'failed'),
        job_started,
        job_finished,
        EXTRACT(EPOCH FROM (COALESCE(job_finished, job_started) - job_started)),
        ujt_ids[(j % array_length(ujt_ids, 1)) + 1],
        content_type_id,
        org_ids[(j % array_length(org_ids, 1)) + 1],
        ee_ids[(j % array_length(ee_ids, 1)) + 1],
        'instance-1-' || random_suffix,
        'instance-1-' || random_suffix,
        '',
        NULL,
        '2.14.0',
        '',
        '/tmp',
        '',
        '',
        gen_random_uuid()::text,
        0,
        false,
        '{}',
        0,
        '{}'
      )
      RETURNING id INTO uj_id;

      -- Create job record (inheritance)
      INSERT INTO main_job (
        unifiedjob_ptr_id, inventory_id, project_id,
        playbook, forks, job_type, verbosity, extra_vars,
        scm_revision, job_tags, skip_tags, "limit", timeout,
        force_handlers, start_at_task, become_enabled,
        allow_simultaneous, artifacts, use_fact_cache,
        diff_mode, job_slice_count, job_slice_number,
        scm_branch, webhook_guid, webhook_service, survey_passwords
      ) VALUES (
        uj_id,
        inventory_ids[(j % array_length(inventory_ids, 1)) + 1],
        NULL,
        'playbook-' || random_suffix || '.yml',
        5,
        'run',
        0,
        '{}',
        '',
        '',
        '',
        '',
        0,
        false,
        '',
        false,
        false,
        '{}',
        false,
        false,
        1,
        0,
        '',
        '',
        '',
        '{}'
      )
      RETURNING unifiedjob_ptr_id INTO job_id;

      job_ids := array_append(job_ids, job_id);

      -- Select random unique hosts for this job
      selected_host_ids := ARRAY[]::INTEGER[];
      FOR k IN 1..hosts_per_job LOOP
        -- Keep trying until we get a unique host
        LOOP
          selected_host_id := host_ids[(floor(random() * array_length(host_ids, 1))::int + 1)];
          -- Check if this host is already selected
          IF NOT (selected_host_id = ANY(selected_host_ids)) THEN
            selected_host_ids := array_append(selected_host_ids, selected_host_id);
            EXIT;
          END IF;
        END LOOP;
      END LOOP;

      -- Create job-host summaries and events
      FOREACH selected_host_id IN ARRAY selected_host_ids LOOP
        SELECT name INTO host_name FROM main_host WHERE id = selected_host_id;

        -- Create job host summary
        INSERT INTO main_jobhostsummary (
          created, modified, host_id, host_name, job_id,
          changed, dark, failures, ok, processed, skipped,
          failed, rescued, ignored
        ) VALUES (
          job_created,
          COALESCE(job_finished, job_started),
          selected_host_id,
          host_name,
          job_id,
          (random() * 5)::int,
          0,
          CASE WHEN job_status = 'failed' THEN (random() * 3)::int + 1 ELSE 0 END,
          CASE WHEN job_status = 'successful' THEN (random() * 10)::int + events_per_job_host ELSE (random() * 5)::int END,
          1,
          (random() * 2)::int,
          (job_status = 'failed'),
          0,
          0
        )
        RETURNING id INTO jhs_id;

        -- Ensure partition exists for this job's timestamp
        partition_name := ensure_jobevent_partition(job_created);

        -- Create events for this job-host pair
        FOR m IN 1..events_per_job_host LOOP
          -- Determine event type based on job status
          IF job_status = 'failed' AND m = events_per_job_host THEN
            event_type := 'runner_on_failed';
            event_failed := true;
            event_changed := false;
          ELSIF job_status = 'successful' THEN
            event_type := event_types[(m % array_length(event_types, 1)) + 1];
            event_failed := (event_type = 'runner_on_failed');
            event_changed := (random() < 0.3);
          ELSE
            event_type := 'runner_on_ok';
            event_failed := false;
            event_changed := (random() < 0.2);
          END IF;

          INSERT INTO main_jobevent (
            created, modified, event, event_data, failed, changed,
            host_name, play, role, task, counter, host_id, job_id,
            uuid, parent_uuid, end_line, playbook, start_line,
            stdout, verbosity, job_created
          ) VALUES (
            job_started + (m * interval '10 seconds'),
            job_started + (m * interval '10 seconds'),
            event_type,
            ('{"task_action": "' || task_actions[(m % array_length(task_actions, 1)) + 1] || '", "duration": ' || (random() * 5)::numeric(5,2) || ', "res": {"changed": ' || event_changed || ', "failed": ' || event_failed || '}}')::text,
            event_failed,
            event_changed,
            host_name,
            'Play-' || (m % 3) + 1,
            'Role-' || (m % 2) + 1,
            'Task-' || m || '-' || task_actions[(m % array_length(task_actions, 1)) + 1],
            m,
            selected_host_id,
            job_id,
            gen_random_uuid()::text,
            gen_random_uuid()::text,
            m * 10,
            'playbook-' || random_suffix || '.yml',
            (m - 1) * 10,
            '',
            0,
            job_created
          );
        END LOOP;
      END LOOP;
    END LOOP;
  END LOOP;

  RAISE NOTICE '  Created % jobs with events', array_length(job_ids, 1);

  -- ========================================
  -- PHASE 5: Metrics and Audit Tables
  -- ========================================
  RAISE NOTICE 'Phase 5/6: Creating host metrics and audit records...';

  -- Create host metrics for all hosts
  FOR i IN 1..LEAST(array_length(host_ids, 1), 100) LOOP  -- Limit to 100 for reasonable size
    SELECT name INTO host_name FROM main_host WHERE id = host_ids[i];

    INSERT INTO main_hostmetric (
      hostname, first_automation, last_automation, last_deleted,
      automated_counter, deleted_counter, deleted, used_in_inventories
    ) VALUES (
      host_name,
      base_date + (random() * interval '1 day'),
      base_date + ((days_to_generate - 1) || ' days')::interval + (random() * interval '1 day'),
      CASE WHEN random() < 0.1 THEN base_date + ((days_to_generate / 2) || ' days')::interval ELSE NULL END,
      (random() * 20)::int + 5,
      CASE WHEN random() < 0.1 THEN (random() * 3)::int ELSE 0 END,
      (random() < 0.1),
      (random() * 5)::int + 1
    );
  END LOOP;
  RAISE NOTICE '  Created host metrics for % hosts', LEAST(array_length(host_ids, 1), 100);

  -- ========================================
  -- PHASE 6: Configuration Settings
  -- ========================================
  RAISE NOTICE 'Phase 6/6: Inserting configuration settings...';

  -- Insert some common configuration settings
  -- Using unique keys with testdata suffix to avoid conflicts
  INSERT INTO conf_setting (created, modified, key, value, user_id)
  VALUES
    (base_date, base_date, 'GALAXY_TASK_ENV-testdata-' || random_suffix, '{"GIT_SSH_COMMAND": "ssh -o StrictHostKeyChecking=no"}', NULL),
    (base_date, base_date, 'TOWER_URL_BASE-testdata-' || random_suffix, '"https://controller.example.com"', NULL);

  RAISE NOTICE '  Created configuration settings';

  -- ========================================
  -- FINAL SUMMARY
  -- ========================================
  RAISE NOTICE '';
  RAISE NOTICE '========================================';
  RAISE NOTICE 'Test Data Generation Complete!';
  RAISE NOTICE '========================================';
  RAISE NOTICE 'Generated data summary:';
  RAISE NOTICE '  Organizations: %', (SELECT COUNT(*) FROM main_organization WHERE name LIKE '%testdata%');
  RAISE NOTICE '  Inventories: %', (SELECT COUNT(*) FROM main_inventory WHERE name LIKE '%testdata%');
  RAISE NOTICE '  Hosts: %', (SELECT COUNT(*) FROM main_host WHERE name LIKE '%testdata%');
  RAISE NOTICE '  Execution Environments: %', (SELECT COUNT(*) FROM main_executionenvironment WHERE name LIKE '%testdata%');
  RAISE NOTICE '  Job Templates: %', (SELECT COUNT(*) FROM main_unifiedjobtemplate WHERE name LIKE '%testdata%');
  RAISE NOTICE '  Jobs: %', (SELECT COUNT(*) FROM main_unifiedjob WHERE name LIKE '%testdata%');
  RAISE NOTICE '  Job-Host Summaries: %', (SELECT COUNT(*) FROM main_jobhostsummary jhs JOIN main_host h ON jhs.host_id = h.id WHERE h.name LIKE '%testdata%');
  RAISE NOTICE '  Job Events: %', (SELECT COUNT(*) FROM main_jobevent WHERE playbook LIKE '%testdata%');
  RAISE NOTICE '  Host Metrics: %', (SELECT COUNT(*) FROM main_hostmetric WHERE hostname LIKE '%testdata%');
  RAISE NOTICE '';
  RAISE NOTICE 'All test data has been successfully generated!';
  RAISE NOTICE 'Data can be identified by the "testdata" suffix in names.';
  RAISE NOTICE '';
  RAISE NOTICE 'To clean up test data, delete records where name/key contains testdata';
  RAISE NOTICE '  Example: DELETE FROM main_organization WHERE name LIKE ''%%testdata%%'';';
  RAISE NOTICE '========================================';

EXCEPTION
  WHEN OTHERS THEN
    RAISE EXCEPTION 'Test data generation failed: % (SQLSTATE: %)', SQLERRM, SQLSTATE;
END;
$$;

-- Clean up helper functions (optional - comment out if you want to keep them)
-- DROP FUNCTION IF EXISTS ensure_jobevent_partition(TIMESTAMP WITH TIME ZONE);
-- DROP FUNCTION IF EXISTS random_ip();
-- DROP FUNCTION IF EXISTS random_timestamp_in_day(TIMESTAMP WITH TIME ZONE);
-- DROP FUNCTION IF EXISTS random_job_status();
