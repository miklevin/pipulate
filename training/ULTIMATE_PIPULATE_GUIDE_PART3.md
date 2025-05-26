# 🚨 **THE ULTIMATE PIPULATE GUIDE - PART 3: EXPERT MASTERY** 🚨

## **PRIORITY 21: Advanced UI Patterns and Widgets**

**Question**: How do you implement sophisticated UI components and interactive widgets?

**Answer**: Pipulate supports advanced UI patterns through FastHTML components and JavaScript integration:

### **Dynamic Form Generation:**
```python
def generate_dynamic_form(self, field_config, step_id, app_name):
    """Generate forms based on configuration"""
    form_elements = []
    
    for field in field_config:
        if field['type'] == 'select':
            form_elements.append(
                Select(
                    *[Option(opt['label'], value=opt['value']) for opt in field['options']],
                    name=field['name'],
                    required=field.get('required', False)
                )
            )
        elif field['type'] == 'textarea':
            form_elements.append(
                Textarea(
                    field.get('placeholder', ''),
                    name=field['name'],
                    rows=field.get('rows', 3),
                    required=field.get('required', False)
                )
            )
        elif field['type'] == 'file':
            form_elements.append(
                Input(
                    type="file",
                    name=field['name'],
                    multiple=field.get('multiple', False),
                    accept=field.get('accept', '*/*')
                )
            )
    
    return Form(
        *form_elements,
        Button('Submit', type='submit'),
        hx_post=f'/{app_name}/{step_id}_submit',
        hx_target=f'#{step_id}',
        enctype="multipart/form-data" if any(f['type'] == 'file' for f in field_config) else None
    )
```

### **Progressive Enhancement with JavaScript:**
```python
def create_enhanced_widget(self, widget_type, data, step_id):
    """Create widgets with JavaScript enhancement"""
    
    if widget_type == 'code_editor':
        return Div(
            Textarea(data.get('content', ''), id=f'editor_{step_id}'),
            Script(f"""
                // Initialize CodeMirror or similar
                const editor = CodeMirror.fromTextArea(
                    document.getElementById('editor_{step_id}'),
                    {{
                        mode: '{data.get('language', 'python')}',
                        theme: 'default',
                        lineNumbers: true
                    }}
                );
            """),
            id=f'widget_{step_id}'
        )
    
    elif widget_type == 'data_table':
        return Div(
            Table(
                Thead(Tr(*[Th(col) for col in data['columns']])),
                Tbody(*[
                    Tr(*[Td(str(cell)) for cell in row])
                    for row in data['rows']
                ])
            ),
            Script(f"""
                // Initialize DataTables or similar
                $('#table_{step_id}').DataTable({{
                    pageLength: 25,
                    searching: true,
                    ordering: true
                }});
            """),
            id=f'table_{step_id}'
        )
```

### **Real-time Updates with WebSockets:**
```python
async def create_realtime_widget(self, step_id, pipeline_id):
    """Widget that updates in real-time"""
    return Div(
        H4("Real-time Status"),
        Div(id=f'status_{step_id}', cls='status-display'),
        Script(f"""
            const ws = new WebSocket('ws://localhost:5001/ws/{pipeline_id}/{step_id}');
            ws.onmessage = function(event) {{
                const data = JSON.parse(event.data);
                document.getElementById('status_{step_id}').innerHTML = data.html;
            }};
        """),
        id=f'realtime_{step_id}'
    )

# WebSocket handler for real-time updates
async def handle_realtime_ws(self, websocket: WebSocket, pipeline_id: str, step_id: str):
    await websocket.accept()
    try:
        while True:
            # Get current status
            status_data = await self.get_realtime_status(pipeline_id, step_id)
            status_html = self.render_status_html(status_data)
            
            await websocket.send_text(json.dumps({
                'html': str(status_html),
                'timestamp': time.time()
            }))
            
            await asyncio.sleep(1)  # Update every second
    except WebSocketDisconnect:
        pass
```

---

## **PRIORITY 22: Advanced Data Processing Patterns**

**Question**: How do you handle complex data transformations and processing pipelines?

**Answer**: Pipulate supports sophisticated data processing through streaming, chunking, and pipeline patterns:

### **Streaming Data Processing:**
```python
async def process_large_dataset(self, file_path, pipeline_id, step_id):
    """Process large files without loading everything into memory"""
    
    async def data_generator():
        with open(file_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                yield line_num, line.strip()
                
                # Update progress every 1000 lines
                if line_num % 1000 == 0:
                    await self.update_progress(pipeline_id, step_id, line_num)
    
    results = []
    async for line_num, line in data_generator():
        # Process each line
        processed = await self.process_line(line)
        results.append(processed)
        
        # Batch save every 10000 records
        if len(results) >= 10000:
            await self.save_batch(pipeline_id, step_id, results)
            results = []
    
    # Save remaining results
    if results:
        await self.save_batch(pipeline_id, step_id, results)

async def update_progress(self, pipeline_id, step_id, current_line):
    """Update processing progress"""
    progress_data = {
        'current_line': current_line,
        'timestamp': time.time(),
        'status': 'processing'
    }
    
    # Store in temporary state
    await pip.set_temp_data(pipeline_id, f'{step_id}_progress', progress_data)
    
    # Broadcast to WebSocket clients
    await self.broadcast_progress(pipeline_id, step_id, progress_data)
```

### **Data Validation and Cleaning:**
```python
class DataValidator:
    """Advanced data validation and cleaning"""
    
    def __init__(self, schema):
        self.schema = schema
        self.errors = []
        self.warnings = []
    
    async def validate_and_clean(self, data):
        """Validate and clean data according to schema"""
        cleaned_data = []
        
        for row_num, row in enumerate(data, 1):
            try:
                cleaned_row = await self.validate_row(row, row_num)
                cleaned_data.append(cleaned_row)
            except ValidationError as e:
                self.errors.append(f"Row {row_num}: {e}")
                continue
        
        return cleaned_data, self.errors, self.warnings
    
    async def validate_row(self, row, row_num):
        """Validate and clean a single row"""
        cleaned_row = {}
        
        for field_name, field_config in self.schema.items():
            value = row.get(field_name)
            
            # Required field check
            if field_config.get('required', False) and not value:
                raise ValidationError(f"Required field '{field_name}' is missing")
            
            # Type conversion and validation
            if value is not None:
                cleaned_value = await self.convert_and_validate_field(
                    value, field_config, field_name, row_num
                )
                cleaned_row[field_name] = cleaned_value
        
        return cleaned_row
    
    async def convert_and_validate_field(self, value, config, field_name, row_num):
        """Convert and validate individual field"""
        field_type = config.get('type', 'string')
        
        if field_type == 'integer':
            try:
                return int(value)
            except ValueError:
                raise ValidationError(f"'{field_name}' must be an integer")
        
        elif field_type == 'float':
            try:
                return float(value)
            except ValueError:
                raise ValidationError(f"'{field_name}' must be a number")
        
        elif field_type == 'email':
            if not self.is_valid_email(value):
                raise ValidationError(f"'{field_name}' must be a valid email")
            return value.lower().strip()
        
        elif field_type == 'url':
            if not self.is_valid_url(value):
                raise ValidationError(f"'{field_name}' must be a valid URL")
            return value.strip()
        
        return str(value).strip()
```

### **Multi-step Data Pipeline:**
```python
class DataPipeline:
    """Multi-stage data processing pipeline"""
    
    def __init__(self, pipeline_id, steps):
        self.pipeline_id = pipeline_id
        self.steps = steps
        self.results = {}
    
    async def execute(self):
        """Execute all pipeline steps in sequence"""
        for step_name, step_config in self.steps.items():
            try:
                result = await self.execute_step(step_name, step_config)
                self.results[step_name] = result
                
                # Save intermediate results
                await self.save_step_result(step_name, result)
                
            except Exception as e:
                await self.handle_step_error(step_name, e)
                raise
    
    async def execute_step(self, step_name, config):
        """Execute a single pipeline step"""
        step_type = config['type']
        input_data = self.get_input_data(config.get('input_from'))
        
        if step_type == 'filter':
            return await self.filter_data(input_data, config['criteria'])
        elif step_type == 'transform':
            return await self.transform_data(input_data, config['transformation'])
        elif step_type == 'aggregate':
            return await self.aggregate_data(input_data, config['aggregation'])
        elif step_type == 'export':
            return await self.export_data(input_data, config['format'])
        else:
            raise ValueError(f"Unknown step type: {step_type}")
    
    def get_input_data(self, input_source):
        """Get input data for a step"""
        if input_source is None:
            return None
        elif input_source in self.results:
            return self.results[input_source]
        else:
            raise ValueError(f"Input source '{input_source}' not found")
```

---

## **PRIORITY 23: Advanced Security and Access Control**

**Question**: How do you implement security, authentication, and access control?

**Answer**: Pipulate supports multiple security layers and access control patterns:

### **Role-Based Access Control:**
```python
class AccessControl:
    """Role-based access control system"""
    
    def __init__(self, db):
        self.db = db
        self.roles = {
            'admin': ['read', 'write', 'delete', 'manage_users'],
            'editor': ['read', 'write'],
            'viewer': ['read']
        }
    
    def check_permission(self, user_id, resource, action):
        """Check if user has permission for action on resource"""
        user_role = self.get_user_role(user_id)
        required_permissions = self.get_resource_permissions(resource, action)
        user_permissions = self.roles.get(user_role, [])
        
        return all(perm in user_permissions for perm in required_permissions)
    
    def require_permission(self, resource, action):
        """Decorator to require specific permissions"""
        def decorator(func):
            async def wrapper(self, request, *args, **kwargs):
                user_id = self.get_current_user(request)
                if not self.access_control.check_permission(user_id, resource, action):
                    return self.unauthorized_response()
                return await func(self, request, *args, **kwargs)
            return wrapper
        return decorator

# Usage in workflow methods
class SecureWorkflow:
    def __init__(self, app, pipulate, pipeline, db, app_name):
        self.access_control = AccessControl(db)
        # ... rest of init
    
    @require_permission('workflow', 'read')
    async def step_01(self, request):
        # Only users with 'read' permission can access
        pass
    
    @require_permission('workflow', 'write')
    async def step_01_submit(self, request):
        # Only users with 'write' permission can submit
        pass
```

### **Data Encryption and Sanitization:**
```python
class DataSecurity:
    """Data encryption and sanitization utilities"""
    
    def __init__(self, encryption_key):
        self.cipher = Fernet(encryption_key)
    
    def encrypt_sensitive_data(self, data):
        """Encrypt sensitive data before storage"""
        if isinstance(data, dict):
            encrypted_data = {}
            for key, value in data.items():
                if self.is_sensitive_field(key):
                    encrypted_data[key] = self.cipher.encrypt(str(value).encode()).decode()
                else:
                    encrypted_data[key] = value
            return encrypted_data
        return data
    
    def decrypt_sensitive_data(self, data):
        """Decrypt sensitive data after retrieval"""
        if isinstance(data, dict):
            decrypted_data = {}
            for key, value in data.items():
                if self.is_sensitive_field(key):
                    try:
                        decrypted_data[key] = self.cipher.decrypt(value.encode()).decode()
                    except:
                        decrypted_data[key] = value  # Fallback for unencrypted data
                else:
                    decrypted_data[key] = value
            return decrypted_data
        return data
    
    def sanitize_input(self, user_input):
        """Sanitize user input to prevent XSS and injection"""
        if isinstance(user_input, str):
            # Remove potentially dangerous characters
            sanitized = re.sub(r'[<>"\']', '', user_input)
            # Limit length
            sanitized = sanitized[:1000]
            return sanitized.strip()
        return user_input
    
    def is_sensitive_field(self, field_name):
        """Determine if a field contains sensitive data"""
        sensitive_patterns = ['password', 'token', 'key', 'secret', 'ssn', 'credit_card']
        return any(pattern in field_name.lower() for pattern in sensitive_patterns)
```

### **Audit Logging:**
```python
class AuditLogger:
    """Comprehensive audit logging system"""
    
    def __init__(self, db):
        self.db = db
    
    async def log_action(self, user_id, action, resource, details=None):
        """Log user actions for audit trail"""
        audit_entry = {
            'timestamp': time.time(),
            'user_id': user_id,
            'action': action,
            'resource': resource,
            'details': details or {},
            'ip_address': self.get_client_ip(),
            'user_agent': self.get_user_agent()
        }
        
        await self.db.insert('audit_log', audit_entry)
    
    async def log_workflow_action(self, pipeline_id, step_id, action, user_id, data=None):
        """Log workflow-specific actions"""
        await self.log_action(
            user_id=user_id,
            action=f'workflow_{action}',
            resource=f'{pipeline_id}/{step_id}',
            details={
                'pipeline_id': pipeline_id,
                'step_id': step_id,
                'data_summary': self.summarize_data(data)
            }
        )
    
    def summarize_data(self, data):
        """Create summary of data for audit log"""
        if not data:
            return None
        
        if isinstance(data, dict):
            return {
                'field_count': len(data),
                'fields': list(data.keys()),
                'data_size': len(str(data))
            }
        
        return {
            'type': type(data).__name__,
            'size': len(str(data))
        }
```

---

## **PRIORITY 24: Advanced Integration Patterns**

**Question**: How do you integrate with external APIs, databases, and services?

**Answer**: Pipulate supports sophisticated integration patterns with proper error handling and resilience:

### **API Integration with Retry Logic:**
```python
class APIIntegration:
    """Robust API integration with retry and circuit breaker"""
    
    def __init__(self, base_url, api_key, max_retries=3):
        self.base_url = base_url
        self.api_key = api_key
        self.max_retries = max_retries
        self.circuit_breaker = CircuitBreaker()
    
    async def make_request(self, endpoint, method='GET', data=None, timeout=30):
        """Make API request with retry logic"""
        
        @self.circuit_breaker
        async def _request():
            async with httpx.AsyncClient(timeout=timeout) as client:
                headers = {
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                }
                
                response = await client.request(
                    method=method,
                    url=f'{self.base_url}/{endpoint}',
                    headers=headers,
                    json=data
                )
                
                response.raise_for_status()
                return response.json()
        
        # Retry with exponential backoff
        for attempt in range(self.max_retries):
            try:
                return await _request()
            except (httpx.HTTPError, httpx.TimeoutException) as e:
                if attempt == self.max_retries - 1:
                    raise APIError(f"API request failed after {self.max_retries} attempts: {e}")
                
                # Exponential backoff
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)
    
    async def batch_request(self, requests, batch_size=10):
        """Process multiple API requests in batches"""
        results = []
        
        for i in range(0, len(requests), batch_size):
            batch = requests[i:i + batch_size]
            
            # Process batch concurrently
            batch_tasks = [
                self.make_request(req['endpoint'], req.get('method', 'GET'), req.get('data'))
                for req in batch
            ]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            results.extend(batch_results)
            
            # Rate limiting
            await asyncio.sleep(0.1)
        
        return results

class CircuitBreaker:
    """Circuit breaker pattern for API resilience"""
    
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'closed'  # closed, open, half-open
    
    def __call__(self, func):
        async def wrapper(*args, **kwargs):
            if self.state == 'open':
                if time.time() - self.last_failure_time > self.timeout:
                    self.state = 'half-open'
                else:
                    raise CircuitBreakerOpenError("Circuit breaker is open")
            
            try:
                result = await func(*args, **kwargs)
                self.on_success()
                return result
            except Exception as e:
                self.on_failure()
                raise
        
        return wrapper
    
    def on_success(self):
        self.failure_count = 0
        self.state = 'closed'
    
    def on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'open'
```

### **Database Integration Patterns:**
```python
class DatabaseIntegration:
    """Advanced database integration with connection pooling"""
    
    def __init__(self, connection_string, pool_size=10):
        self.connection_string = connection_string
        self.pool = None
        self.pool_size = pool_size
    
    async def initialize_pool(self):
        """Initialize connection pool"""
        self.pool = await asyncpg.create_pool(
            self.connection_string,
            min_size=1,
            max_size=self.pool_size
        )
    
    async def execute_query(self, query, params=None):
        """Execute query with connection from pool"""
        async with self.pool.acquire() as connection:
            return await connection.fetch(query, *(params or []))
    
    async def execute_transaction(self, operations):
        """Execute multiple operations in a transaction"""
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                results = []
                for operation in operations:
                    result = await connection.fetch(
                        operation['query'],
                        *operation.get('params', [])
                    )
                    results.append(result)
                return results
    
    async def bulk_insert(self, table, data, batch_size=1000):
        """Efficient bulk insert with batching"""
        async with self.pool.acquire() as connection:
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                
                # Prepare bulk insert query
                columns = list(batch[0].keys())
                placeholders = ', '.join([f'${i+1}' for i in range(len(columns))])
                query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
                
                # Execute batch
                await connection.executemany(
                    query,
                    [tuple(row[col] for col in columns) for row in batch]
                )
```

### **Message Queue Integration:**
```python
class MessageQueueIntegration:
    """Integration with message queues for async processing"""
    
    def __init__(self, queue_url):
        self.queue_url = queue_url
        self.connection = None
    
    async def connect(self):
        """Connect to message queue"""
        self.connection = await aio_pika.connect_robust(self.queue_url)
        self.channel = await self.connection.channel()
    
    async def publish_message(self, queue_name, message, priority=0):
        """Publish message to queue"""
        queue = await self.channel.declare_queue(queue_name, durable=True)
        
        await self.channel.default_exchange.publish(
            aio_pika.Message(
                json.dumps(message).encode(),
                priority=priority,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=queue_name
        )
    
    async def consume_messages(self, queue_name, callback):
        """Consume messages from queue"""
        queue = await self.channel.declare_queue(queue_name, durable=True)
        
        async def message_handler(message):
            async with message.process():
                try:
                    data = json.loads(message.body.decode())
                    await callback(data)
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    raise
        
        await queue.consume(message_handler)
```

---

## **PRIORITY 25: Production Deployment and Scaling**

**Question**: How do you deploy and scale Pipulate applications in production?

**Answer**: Production deployment requires careful consideration of performance, reliability, and scalability:

### **Production Configuration:**
```python
# production_config.py
class ProductionConfig:
    """Production-specific configuration"""
    
    # Server settings
    HOST = "0.0.0.0"
    PORT = 8000
    WORKERS = 4
    
    # Database settings
    DATABASE_URL = os.getenv("DATABASE_URL")
    DATABASE_POOL_SIZE = 20
    
    # Security settings
    SECRET_KEY = os.getenv("SECRET_KEY")
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
    
    # Logging settings
    LOG_LEVEL = "INFO"
    LOG_FILE = "/var/log/pipulate/app.log"
    
    # Performance settings
    CACHE_TTL = 3600
    MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100MB
    
    # Monitoring settings
    METRICS_ENABLED = True
    HEALTH_CHECK_ENDPOINT = "/health"

# production_server.py
async def create_production_app():
    """Create production-ready application"""
    
    # Initialize with production config
    config = ProductionConfig()
    
    # Setup logging
    logger.configure(
        handlers=[
            {"sink": config.LOG_FILE, "level": config.LOG_LEVEL, "rotation": "1 day"},
            {"sink": sys.stdout, "level": config.LOG_LEVEL}
        ]
    )
    
    # Initialize database pool
    db_pool = await asyncpg.create_pool(
        config.DATABASE_URL,
        min_size=5,
        max_size=config.DATABASE_POOL_SIZE
    )
    
    # Create FastHTML app with production settings
    app = FastHTML(
        debug=False,
        default_hdrs=False,  # Disable default headers for performance
    )
    
    # Add middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://yourdomain.com"],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["yourdomain.com", "*.yourdomain.com"]
    )
    
    # Add health check endpoint
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "timestamp": time.time()}
    
    return app
```

### **Docker Deployment:**
```dockerfile
# Dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd --create-home --shell /bin/bash app

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Change ownership to app user
RUN chown -R app:app /app

# Switch to app user
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start application
CMD ["uvicorn", "production_server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### **Kubernetes Deployment:**
```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pipulate-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: pipulate-app
  template:
    metadata:
      labels:
        app: pipulate-app
    spec:
      containers:
      - name: pipulate-app
        image: your-registry/pipulate:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: pipulate-secrets
              key: database-url
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: pipulate-secrets
              key: secret-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: pipulate-service
spec:
  selector:
    app: pipulate-app
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

### **Monitoring and Observability:**
```python
class ProductionMonitoring:
    """Production monitoring and metrics"""
    
    def __init__(self):
        self.metrics = {}
        self.start_time = time.time()
    
    def track_request(self, endpoint, method, duration, status_code):
        """Track request metrics"""
        key = f"{method}_{endpoint}"
        
        if key not in self.metrics:
            self.metrics[key] = {
                'count': 0,
                'total_duration': 0,
                'errors': 0
            }
        
        self.metrics[key]['count'] += 1
        self.metrics[key]['total_duration'] += duration
        
        if status_code >= 400:
            self.metrics[key]['errors'] += 1
    
    def get_metrics(self):
        """Get current metrics"""
        uptime = time.time() - self.start_time
        
        return {
            'uptime_seconds': uptime,
            'endpoints': {
                endpoint: {
                    'requests_total': data['count'],
                    'avg_duration_ms': (data['total_duration'] / data['count'] * 1000) if data['count'] > 0 else 0,
                    'error_rate': (data['errors'] / data['count']) if data['count'] > 0 else 0
                }
                for endpoint, data in self.metrics.items()
            }
        }
    
    async def export_metrics(self):
        """Export metrics in Prometheus format"""
        metrics = self.get_metrics()
        
        prometheus_metrics = []
        prometheus_metrics.append(f"pipulate_uptime_seconds {metrics['uptime_seconds']}")
        
        for endpoint, data in metrics['endpoints'].items():
            prometheus_metrics.append(f'pipulate_requests_total{{endpoint="{endpoint}"}} {data["requests_total"]}')
            prometheus_metrics.append(f'pipulate_request_duration_ms{{endpoint="{endpoint}"}} {data["avg_duration_ms"]}')
            prometheus_metrics.append(f'pipulate_error_rate{{endpoint="{endpoint}"}} {data["error_rate"]}')
        
        return '\n'.join(prometheus_metrics)

# Middleware for automatic metrics collection
class MetricsMiddleware:
    def __init__(self, app, monitoring):
        self.app = app
        self.monitoring = monitoring
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        start_time = time.time()
        
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                duration = time.time() - start_time
                self.monitoring.track_request(
                    endpoint=scope["path"],
                    method=scope["method"],
                    duration=duration,
                    status_code=message["status"]
                )
            await send(message)
        
        await self.app(scope, receive, send_wrapper)
```

---

## **EXPERT MASTERY SUMMARY**

### **🏆 The 25 Patterns That Define Pipulate Mastery:**

1. **Auto-Key Generation** - HX-Refresh for empty input
2. **Three-Phase Step Pattern** - Finalize/Revert/Input logic
3. **Pipeline Key System** - Structured data identification
4. **Step namedtuple Structure** - Workflow definition
5. **State Management** - JSON persistence patterns
6. **Chain Reaction Pattern** - HTMX-driven progression
7. **Request Parameter Requirement** - FastHTML integration
8. **DictLikeDB vs Pipeline** - Storage system distinction
9. **Workflow Registration** - Plugin discovery system
10. **Message Queue System** - LLM integration
11. **Finalization System** - Workflow lifecycle management
12. **Revert System** - User experience patterns
13. **File Operations** - Secure data handling
14. **Environment Integration** - Nix development setup
15. **Plugin Development** - Structured creation process
16. **Error Handling** - Multi-layered debugging
17. **WET vs DRY Philosophy** - Design principles
18. **Browser Automation** - Selenium integration
19. **Local LLM Integration** - Ollama patterns
20. **Advanced State Management** - Complex data patterns
21. **Advanced UI Patterns** - Sophisticated components
22. **Data Processing** - Streaming and validation
23. **Security and Access Control** - Production-ready security
24. **Integration Patterns** - External service connectivity
25. **Production Deployment** - Scaling and monitoring

### **🎯 The Ultimate Pipulate Developer:**

A master Pipulate developer understands that this framework is fundamentally different from traditional web development. They recognize that:

- **Local-first operation** takes precedence over cloud-native patterns
- **Explicit state management** is preferred over implicit abstractions
- **Notebook-like linear progression** guides the user experience
- **WET workflows** provide clarity over DRY abstractions
- **Three-phase step logic** is the architectural foundation
- **Chain reaction patterns** create seamless user flows
- **Auto-key generation** enables frictionless workflow initiation

### **🚀 Beyond the Patterns:**

True mastery comes from understanding not just the "how" but the "why" behind each pattern. Pipulate's design philosophy prioritizes:

1. **Developer Experience** - Clear, explicit patterns over magic
2. **User Experience** - Seamless, notebook-like workflows
3. **Data Integrity** - Persistent, recoverable state management
4. **Local Control** - Independence from cloud services
5. **Extensibility** - Plugin-based architecture for customization

The ultimate Pipulate implementation combines all these patterns into cohesive, production-ready applications that deliver exceptional user experiences while maintaining the simplicity and clarity that makes the framework unique.

**Remember**: Mastery isn't about using every pattern in every project—it's about choosing the right patterns for each specific use case and implementing them with precision and understanding. 