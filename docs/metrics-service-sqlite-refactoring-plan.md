# Metrics Service (MS) Storage and Exposure Refactoring - Implementation Plan

## Executive Summary

This document outlines the implementation plan for refactoring the Metrics Service (MS) to replace CSV-based metrics collection with a dedicated SQLite database (`metricsStorage.sqlite`) and expose the data via new API endpoints.

**Status**: Planning Phase
**Target**: Replace CSV files with SQLite, expose data via `/api/v1/metrics-data/` endpoints
**Impact**: Medium-High (core data storage architecture change)

---

## 1. Project Overview

### Current State
- Metrics collected by `collect_metrics` task → saved to CSV files
- Core application data in shared PostgreSQL instance
- No structured API for metrics consumption

### Target State
- Metrics collected by `collect_metrics` task → saved to SQLite database
- Dedicated `metricsStorage.sqlite` database for metrics only
- New API endpoints for BI tools and UIs
- Read-only BI user authentication
- PostgreSQL used only for core application data

### Benefits
- ✅ **Data Isolation**: Metrics separated from application data
- ✅ **Performance**: No contention on shared PostgreSQL
- ✅ **Queryability**: Structured access vs. flat files
- ✅ **Security**: Dedicated read-only BI access
- ✅ **Scalability**: SQLite optimized for read-heavy workloads

---

## 2. Implementation Phases

### Phase 1: Database Design & Models (Tasks 1-5)
**Goal**: Establish SQLite database and Django models

#### Task 1.1: Design Database Schema
- Identify all metric types currently collected
- Design normalized schema with tables:
  - `metrics_data` - Core metrics records
  - `metric_sources` - Source identifiers (hosts, services)
  - `metric_types` - Metric type definitions
  - `collection_runs` - Metadata about collection jobs
- Document relationships and indexes
- Consider time-series optimization patterns

**Schema Considerations**:
```python
# Proposed models structure
class MetricType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    unit = models.CharField(max_length=50)

class MetricSource(models.Model):
    source_type = models.CharField(max_length=50)  # host, service, job
    source_id = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict)

class CollectionRun(models.Model):
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True)
    status = models.CharField(max_length=20)
    metrics_collected = models.IntegerField(default=0)

class MetricData(models.Model):
    metric_type = models.ForeignKey(MetricType, on_delete=models.CASCADE)
    source = models.ForeignKey(MetricSource, on_delete=models.CASCADE)
    collection_run = models.ForeignKey(CollectionRun, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(db_index=True)
    value = models.FloatField()
    metadata = models.JSONField(default=dict)

    class Meta:
        indexes = [
            models.Index(fields=['timestamp', 'metric_type']),
            models.Index(fields=['source', 'timestamp']),
        ]
```

#### Task 1.2: Create Django App
```bash
# Inside Metrics Service codebase
cd metrics_service/
python manage.py startapp metrics_storage
```

Update `INSTALLED_APPS` in settings:
```python
INSTALLED_APPS = [
    # ... existing apps
    'apps.metrics_storage',
]
```

#### Task 1.3: Define Models
- Implement models in `apps/metrics_storage/models.py`
- Add model managers for common queries
- Implement `__str__` methods for admin interface
- Add model validation

#### Task 1.4: Configure Database Router
Create database router to direct metrics_storage queries to SQLite:

```python
# metrics_service/settings/database_router.py
class MetricsStorageRouter:
    """Route metrics_storage app to SQLite database"""

    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'metrics_storage':
            return 'metrics_storage'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'metrics_storage':
            return 'metrics_storage'
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'metrics_storage':
            return db == 'metrics_storage'
        return None
```

Update settings:
```python
DATABASES = {
    'default': {
        # Existing PostgreSQL config
    },
    'metrics_storage': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'metricsStorage.sqlite',
    }
}

DATABASE_ROUTERS = ['metrics_service.settings.database_router.MetricsStorageRouter']
```

#### Task 1.5: Create & Apply Migrations
```bash
python manage.py makemigrations metrics_storage
python manage.py migrate --database=metrics_storage
```

---

### Phase 2: Data Ingestion Refactoring (Tasks 6-8)
**Goal**: Migrate collect_metrics from CSV to SQLite

#### Task 2.1: Analyze Current CSV Collection
- Document current CSV structure and fields
- Map CSV columns to Django model fields
- Identify data transformations needed
- Review Metrics Utility (MU) interface

**Current Flow**:
```
collect_metrics task → MU library → writes CSV files
```

**Target Flow**:
```
collect_metrics task → MU library → returns data dict → Django ORM → SQLite
```

#### Task 2.2: Refactor collect_metrics Task
Location: `apps/core/tasks.py` (or equivalent)

```python
from apps.metrics_storage.models import MetricData, CollectionRun, MetricType, MetricSource

def collect_metrics():
    """Refactored to use SQLite storage"""
    # Create collection run record
    run = CollectionRun.objects.using('metrics_storage').create(
        status='running'
    )

    try:
        # Call MU library to gather metrics
        metrics_data = metrics_utility.gather_metrics()

        # Transform and save to database
        for metric in metrics_data:
            metric_type, _ = MetricType.objects.using('metrics_storage').get_or_create(
                name=metric['type'],
                defaults={'description': metric.get('description', ''), 'unit': metric.get('unit', '')}
            )

            source, _ = MetricSource.objects.using('metrics_storage').get_or_create(
                source_type=metric['source_type'],
                source_id=metric['source_id']
            )

            MetricData.objects.using('metrics_storage').create(
                metric_type=metric_type,
                source=source,
                collection_run=run,
                timestamp=metric['timestamp'],
                value=metric['value'],
                metadata=metric.get('metadata', {})
            )

        # Mark run complete
        run.status = 'completed'
        run.metrics_collected = len(metrics_data)
        run.completed_at = timezone.now()
        run.save(using='metrics_storage')

    except Exception as e:
        run.status = 'failed'
        run.save(using='metrics_storage')
        raise
```

#### Task 2.3: Update Metrics Utility Interface (if needed)
If MU currently writes files directly:
- Modify MU to return structured data instead
- Ensure backward compatibility if MU is used elsewhere
- Update MU tests

#### Task 2.4: Implement Data Migration from CSV
Create management command to migrate historical CSV data:

```bash
python manage.py migrate_csv_to_sqlite --csv-dir=/path/to/csvs --batch-size=1000
```

```python
# apps/metrics_storage/management/commands/migrate_csv_to_sqlite.py
from django.core.management.base import BaseCommand
import csv
from apps.metrics_storage.models import MetricData

class Command(BaseCommand):
    help = 'Migrate CSV metrics to SQLite database'

    def add_arguments(self, parser):
        parser.add_argument('--csv-dir', type=str, required=True)
        parser.add_argument('--batch-size', type=int, default=1000)

    def handle(self, *args, **options):
        # Read CSV files and bulk create records
        # Use bulk_create for performance
        pass
```

---

### Phase 3: API Endpoint Implementation (Tasks 9-12)
**Goal**: Create BI and UI endpoints with filtering and optimization

#### Task 3.1: Design API Architecture

**Endpoint Structure**:
```
/api/v1/metrics-data/
├── bi/
│   ├── GET / (list metrics with extensive filtering)
│   └── GET /{id}/ (single metric detail)
└── ui/
    ├── GET /summary/ (aggregated summaries)
    └── GET /recent/ (recent metrics)
```

#### Task 3.2: Implement BI Endpoint
Location: `apps/api/v1/metrics_data/views.py`

```python
from rest_framework import viewsets, filters
from rest_framework.pagination import CursorPagination
from apps.metrics_storage.models import MetricData
from .serializers import MetricDataSerializer

class MetricDataCursorPagination(CursorPagination):
    page_size = 1000
    page_size_query_param = 'page_size'
    max_page_size = 10000
    ordering = '-timestamp'

class BIMetricDataViewSet(viewsets.ReadOnlyModelViewSet):
    """
    BI-optimized endpoint for metrics data export

    Query Parameters:
    - start_date: ISO 8601 datetime
    - end_date: ISO 8601 datetime
    - metric_type: Metric type name
    - source_id: Source identifier
    - page_size: Records per page (default 1000, max 10000)
    """
    serializer_class = MetricDataSerializer
    pagination_class = MetricDataCursorPagination
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['timestamp', 'metric_type', 'value']

    def get_queryset(self):
        queryset = MetricData.objects.using('metrics_storage').select_related(
            'metric_type', 'source', 'collection_run'
        ).all()

        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)

        # Filter by metric type
        metric_type = self.request.query_params.get('metric_type')
        if metric_type:
            queryset = queryset.filter(metric_type__name=metric_type)

        # Filter by source
        source_id = self.request.query_params.get('source_id')
        if source_id:
            queryset = queryset.filter(source__source_id=source_id)

        return queryset
```

Serializer:
```python
from rest_framework import serializers
from apps.metrics_storage.models import MetricData

class MetricDataSerializer(serializers.ModelSerializer):
    metric_type_name = serializers.CharField(source='metric_type.name', read_only=True)
    source_id = serializers.CharField(source='source.source_id', read_only=True)

    class Meta:
        model = MetricData
        fields = [
            'id', 'timestamp', 'value',
            'metric_type_name', 'source_id', 'metadata'
        ]
        read_only_fields = fields
```

#### Task 3.3: Implement UI Endpoint

```python
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Avg, Sum, Count, Max, Min
from django.utils import timezone
from datetime import timedelta

class UIMetricDataViewSet(viewsets.ViewSet):
    """UI-optimized endpoint with aggregations"""

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Return aggregated metrics summary

        Query Parameters:
        - period: hour, day, week, month (default: day)
        - metric_type: Filter by metric type
        """
        period = request.query_params.get('period', 'day')
        metric_type = request.query_params.get('metric_type')

        # Calculate time range
        now = timezone.now()
        period_map = {
            'hour': timedelta(hours=1),
            'day': timedelta(days=1),
            'week': timedelta(weeks=1),
            'month': timedelta(days=30),
        }
        start_time = now - period_map.get(period, timedelta(days=1))

        # Query metrics
        queryset = MetricData.objects.using('metrics_storage').filter(
            timestamp__gte=start_time
        )

        if metric_type:
            queryset = queryset.filter(metric_type__name=metric_type)

        # Aggregate
        summary = queryset.aggregate(
            avg_value=Avg('value'),
            max_value=Max('value'),
            min_value=Min('value'),
            total_count=Count('id')
        )

        return Response({
            'period': period,
            'start_time': start_time,
            'end_time': now,
            'metric_type': metric_type,
            'summary': summary
        })

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Return most recent metrics (last 100)"""
        limit = int(request.query_params.get('limit', 100))

        recent_metrics = MetricData.objects.using('metrics_storage').select_related(
            'metric_type', 'source'
        ).order_by('-timestamp')[:limit]

        serializer = MetricDataSerializer(recent_metrics, many=True)
        return Response(serializer.data)
```

#### Task 3.4: Register URLs

```python
# apps/api/v1/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .metrics_data.views import BIMetricDataViewSet, UIMetricDataViewSet

router = DefaultRouter()
router.register(r'metrics-data/bi', BIMetricDataViewSet, basename='metrics-bi')
router.register(r'metrics-data/ui', UIMetricDataViewSet, basename='metrics-ui')

urlpatterns = [
    path('v1/', include(router.urls)),
]
```

---

### Phase 4: Security & Authentication (Tasks 13-14)
**Goal**: Implement read-only BI user with restricted access

#### Task 4.1: Design Authentication Strategy

**Option A: API Key Authentication** (Recommended)
```python
# apps/api/authentication.py
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth.models import User

class BIAPIKeyAuthentication(BaseAuthentication):
    """API Key authentication for BI users"""

    def authenticate(self, request):
        api_key = request.META.get('HTTP_X_BI_API_KEY')
        if not api_key:
            return None

        # Validate API key against stored hash
        try:
            user = User.objects.get(username='bi_readonly', is_active=True)
            # Verify API key hash
            if not user.profile.verify_api_key(api_key):
                raise AuthenticationFailed('Invalid API key')
            return (user, None)
        except User.DoesNotExist:
            raise AuthenticationFailed('Invalid API key')
```

**Option B: Token Authentication**
- Use DRF TokenAuthentication
- Create dedicated BI user with token
- Simpler but less secure for long-term use

#### Task 4.2: Implement Read-Only Permissions

```python
# apps/api/permissions.py
from rest_framework import permissions

class BIReadOnlyPermission(permissions.BasePermission):
    """
    Read-only permission for BI users
    Only allows GET, HEAD, OPTIONS requests
    """

    def has_permission(self, request, view):
        # Allow read-only methods
        if request.method in permissions.SAFE_METHODS:
            return True

        # Deny all write operations
        return False

    def has_object_permission(self, request, view, obj):
        # Read-only access to all objects
        return request.method in permissions.SAFE_METHODS
```

Apply to BI endpoint:
```python
class BIMetricDataViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = [BIAPIKeyAuthentication]
    permission_classes = [BIReadOnlyPermission]
    # ... rest of implementation
```

#### Task 4.3: Create BI User Setup Command

```python
# apps/metrics_storage/management/commands/create_bi_user.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group, Permission
import secrets

class Command(BaseCommand):
    help = 'Create read-only BI user with API key'

    def handle(self, *args, **options):
        # Create BI user
        user, created = User.objects.get_or_create(
            username='bi_readonly',
            defaults={
                'is_active': True,
                'is_staff': False,
                'is_superuser': False
            }
        )

        if created:
            # Generate API key
            api_key = secrets.token_urlsafe(32)
            user.profile.set_api_key(api_key)

            # Assign read-only permissions
            read_permissions = Permission.objects.filter(
                codename__startswith='view_',
                content_type__app_label='metrics_storage'
            )
            user.user_permissions.set(read_permissions)

            self.stdout.write(self.style.SUCCESS(
                f'BI user created successfully\n'
                f'Username: bi_readonly\n'
                f'API Key: {api_key}\n'
                f'Store this API key securely - it will not be shown again'
            ))
        else:
            self.stdout.write(self.style.WARNING('BI user already exists'))
```

Usage:
```bash
python manage.py create_bi_user
```

---

### Phase 5: Testing (Tasks 15-19)
**Goal**: Comprehensive test coverage for all changes

#### Test Categories

**5.1 Model Tests** (`tests/unit/metrics_storage/test_models.py`)
```python
import pytest
from apps.metrics_storage.models import MetricData, MetricType, MetricSource
from django.utils import timezone

@pytest.mark.django_db(databases=['metrics_storage'])
class TestMetricDataModel:
    def test_create_metric_data(self):
        metric_type = MetricType.objects.using('metrics_storage').create(
            name='cpu_usage',
            description='CPU usage percentage',
            unit='percent'
        )
        source = MetricSource.objects.using('metrics_storage').create(
            source_type='host',
            source_id='host-001'
        )

        metric = MetricData.objects.using('metrics_storage').create(
            metric_type=metric_type,
            source=source,
            timestamp=timezone.now(),
            value=75.5
        )

        assert metric.id is not None
        assert metric.value == 75.5

    def test_metric_data_indexes(self):
        # Verify indexes are created correctly
        pass
```

**5.2 Task Integration Tests** (`tests/integration/test_collect_metrics.py`)
```python
@pytest.mark.django_db(databases=['default', 'metrics_storage'])
def test_collect_metrics_task_creates_records():
    # Run collect_metrics task
    result = collect_metrics()

    # Verify data in SQLite
    metrics_count = MetricData.objects.using('metrics_storage').count()
    assert metrics_count > 0

    # Verify collection run record
    run = CollectionRun.objects.using('metrics_storage').latest('started_at')
    assert run.status == 'completed'
    assert run.metrics_collected == metrics_count
```

**5.3 API Tests** (`tests/api/v1/test_metrics_data_endpoints.py`)
```python
from rest_framework.test import APITestCase
from django.urls import reverse

class BIEndpointTests(APITestCase):
    databases = ['default', 'metrics_storage']

    def setUp(self):
        # Create test data
        self.create_test_metrics()
        # Set API key header
        self.client.credentials(HTTP_X_BI_API_KEY='test-key')

    def test_bi_endpoint_returns_metrics(self):
        url = reverse('metrics-bi-list')
        response = self.client.get(url)

        assert response.status_code == 200
        assert 'results' in response.data

    def test_bi_endpoint_filtering_by_date(self):
        url = reverse('metrics-bi-list')
        response = self.client.get(url, {
            'start_date': '2024-01-01T00:00:00Z',
            'end_date': '2024-12-31T23:59:59Z'
        })

        assert response.status_code == 200

    def test_bi_endpoint_read_only(self):
        url = reverse('metrics-bi-list')
        response = self.client.post(url, {})

        assert response.status_code == 405  # Method not allowed
```

**5.4 Permission Tests**
```python
def test_bi_user_cannot_write():
    # Attempt write operations as BI user
    # Verify all fail
    pass

def test_bi_user_can_read():
    # Verify BI user can access all read endpoints
    pass
```

**5.5 Performance Tests**
```python
@pytest.mark.performance
def test_bi_endpoint_large_dataset():
    # Create 100k records
    # Query with pagination
    # Verify response time < 2 seconds
    pass
```

---

### Phase 6: Documentation (Tasks 20-22)
**Goal**: Complete documentation update

#### Documentation Deliverables

**6.1 Architecture Documentation**
Update `/docs/architecture.md` or create `/docs/metrics-storage-architecture.md`:
- Database schema diagrams
- Data flow diagrams
- Architecture decision records (ADRs)

**6.2 API Documentation**
Update `/docs/api.md` or OpenAPI schema:
```yaml
/api/v1/metrics-data/bi/:
  get:
    summary: Retrieve metrics for BI tools
    parameters:
      - name: start_date
        in: query
        schema:
          type: string
          format: date-time
      - name: end_date
        in: query
        schema:
          type: string
          format: date-time
      - name: metric_type
        in: query
        schema:
          type: string
    responses:
      200:
        description: Paginated list of metrics
```

**6.3 Setup Guide**
Create `/docs/bi-user-setup.md`:
- How to create BI user
- How to generate API keys
- Example API requests with curl/Python
- Security best practices

**6.4 Migration Guide**
Create `/docs/csv-to-sqlite-migration.md`:
- Pre-migration checklist
- Migration commands
- Verification steps
- Rollback procedures

**6.5 Update CLAUDE.md**
Add sections for:
- New metrics_storage app
- SQLite database configuration
- API endpoints usage
- BI user management

---

### Phase 7: Cleanup & Deprecation (Tasks 23-24)
**Goal**: Remove old CSV logic and verify completion

#### Task 7.1: Remove CSV Code
1. Identify all CSV-related code paths
2. Remove or comment out CSV writes
3. Update tests to remove CSV assertions
4. Remove CSV file cleanup jobs (if any)

#### Task 7.2: Final Verification Checklist
- [ ] metricsStorage.sqlite file exists and is writable
- [ ] Django migrations applied successfully
- [ ] collect_metrics task writes to SQLite
- [ ] No CSV files being created
- [ ] BI endpoint returns data correctly
- [ ] UI endpoint returns aggregations
- [ ] Filtering works on all endpoints
- [ ] Pagination works correctly
- [ ] BI user authentication works
- [ ] BI user restricted to read-only
- [ ] All tests passing (unit, integration, API)
- [ ] Documentation complete and accurate
- [ ] Performance benchmarks met

---

## 3. Risk Assessment & Mitigation

### Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Data loss during migration | High | Low | Comprehensive backups, migration testing, rollback plan |
| Performance degradation | Medium | Medium | Load testing, indexing strategy, query optimization |
| Breaking existing consumers | High | Low | No existing API consumers (new endpoints) |
| SQLite file corruption | Medium | Low | Regular backups, WAL mode, proper locking |
| Authentication bypass | High | Low | Security review, penetration testing |

### Mitigation Strategies

1. **Backup Strategy**: Automated backups of metricsStorage.sqlite before migrations
2. **Rollback Plan**: Keep CSV collection code for 1-2 releases, feature flag new system
3. **Performance Monitoring**: Add metrics for query times, database size
4. **Security Audit**: Third-party review of authentication implementation

---

## 4. Success Criteria

### Functional Requirements
- ✅ All metrics saved to SQLite instead of CSV
- ✅ BI endpoint serves filtered, paginated data
- ✅ UI endpoint provides aggregated summaries
- ✅ BI user has read-only access

### Non-Functional Requirements
- ✅ BI endpoint response time < 2 seconds for 10k records
- ✅ Database file size manageable (< 5GB for 1 year data)
- ✅ Test coverage > 80%
- ✅ Zero data loss during migration
- ✅ API uptime > 99.9%

### Documentation Requirements
- ✅ Architecture documented
- ✅ API endpoints documented
- ✅ BI user setup guide complete
- ✅ Migration guide available

---

## 5. Timeline Estimate

| Phase | Tasks | Estimated Effort | Dependencies |
|-------|-------|-----------------|--------------|
| Phase 1: Database & Models | 5 tasks | 3-5 days | None |
| Phase 2: Data Ingestion | 3 tasks | 3-4 days | Phase 1 complete |
| Phase 3: API Endpoints | 4 tasks | 4-6 days | Phase 1 complete |
| Phase 4: Security | 2 tasks | 2-3 days | Phase 3 complete |
| Phase 5: Testing | 5 tasks | 4-5 days | Phases 1-4 complete |
| Phase 6: Documentation | 3 tasks | 2-3 days | Phases 1-5 complete |
| Phase 7: Cleanup | 2 tasks | 1-2 days | All phases complete |
| **Total** | **24 tasks** | **19-28 days** | Sequential |

**Note**: Estimates assume 1 developer working full-time. Adjust for team size and concurrent work.

---

## 6. Next Steps

### Immediate Actions
1. ✅ Review and approve this implementation plan
2. ⏳ Set up development branch: `feature/sqlite-metrics-storage`
3. ⏳ Create project tracking board with all 24 tasks
4. ⏳ Begin Phase 1: Database Design & Models

### Questions to Resolve
- [ ] Confirm SQLite file location (container persistent volume?)
- [ ] Decide on data retention policy (how long to keep metrics?)
- [ ] Choose authentication method (API Key vs Token?)
- [ ] Define backup strategy for SQLite file
- [ ] Determine rollback strategy if issues arise

---

## 7. References

- Django Database Routers: https://docs.djangoproject.com/en/stable/topics/db/multi-db/
- DRF Authentication: https://www.django-rest-framework.org/api-guide/authentication/
- SQLite Performance: https://www.sqlite.org/performance.html
- Metrics Service Current Codebase: [Link to repo]

---

**Document Version**: 1.0
**Last Updated**: 2025-12-05
**Author**: Claude Code
**Status**: Draft - Pending Approval
