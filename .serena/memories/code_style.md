# Code Style & Conventions

## Python (Backend)

### Formatting & Linting
- **Formatter**: ruff
- **Linter**: ruff
- **Type Checker**: ty
- Run with `./fix.sh` or `uv run ruff format .`

### Naming Conventions
- **Files**: `snake_case.py`
- **Classes**: `PascalCase`
- **Functions**: `snake_case()`
- **Variables**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`

### Code Organization
- One router per domain (services, traces, logs, etc.)
- Routers in `server/routers/`
- Models in `server/models/`
- Services in `server/services/`
- Configuration in `server/config.py`

### Type Hints
- Always use type hints for function parameters and return values
- Use `typing` module for complex types
- Example:
  ```python
  from typing import List, Optional
  
  async def get_services(
      time_range: str,
      limit: Optional[int] = None
  ) -> List[Service]:
      ...
  ```

### Docstrings
- Use docstrings for public functions and classes
- Format: Google style or simple description
- Example:
  ```python
  def get_data_manager(user_token: str):
      """
      Get appropriate data manager based on DATA_BACKEND config.
      
      Args:
          user_token: User OAuth token for authentication
          
      Returns:
          LakebaseManager or WarehouseManager instance
      """
  ```

### FastAPI Patterns
- Use dependency injection for authentication
- Extract user token from headers: `request.headers.get("X-Forwarded-Access-Token")`
- Use Pydantic models for request/response validation
- Add router tags for API documentation

## TypeScript (Frontend)

### Formatting & Linting
- **Formatter**: prettier
- **Linter**: ESLint
- Run with `./fix.sh` or `cd client && bun run format`

### Naming Conventions
- **Files**: `PascalCase.tsx` for components, `camelCase.ts` for utilities
- **Components**: `PascalCase`
- **Functions**: `camelCase()`
- **Variables**: `camelCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Types/Interfaces**: `PascalCase`

### Code Organization
- Components in `client/src/components/`
- Pages in `client/src/pages/`
- Types in `client/src/types/`
- Auto-generated client in `client/src/fastapi_client.ts`

### Type Safety
- **NEVER use `any` type**
- Always define interfaces for data structures
- Use TypeScript strict mode
- Example:
  ```typescript
  interface Service {
    service_name: string;
    request_count: number;
    error_rate: number;
  }
  
  const fetchServices = async (): Promise<Service[]> => {
    ...
  }
  ```

### React Patterns
- Use functional components with hooks
- Use React Query for data fetching
- Use shadcn/ui components for UI
- Keep components small and focused
- Example:
  ```typescript
  export function ServiceList() {
    const { data, isLoading } = useQuery({
      queryKey: ['services'],
      queryFn: fetchServices
    });
    
    if (isLoading) return <div>Loading...</div>;
    
    return (
      <div>
        {data?.map(service => (
          <ServiceCard key={service.service_name} service={service} />
        ))}
      </div>
    );
  }
  ```

### Import Organization
1. React imports
2. Third-party libraries
3. Internal components
4. Types/interfaces
5. Styles

Example:
```typescript
import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card } from '@/components/ui/card';
import { Service } from '@/types/service';
import './styles.css';
```

## SQL Queries

### Lakebase (PostgreSQL)
- Use PostgreSQL syntax
- Cast with `::` operator: `(value)::float`
- JSONB operators: `->>` for text, `->` for JSONB
- Array expansion: `jsonb_array_elements()`
- Quote identifiers with double quotes: `"errorRate"`

### Spark SQL (Warehouse)
- Use Spark SQL syntax
- Cast with `CAST()`: `CAST(value AS FLOAT)`
- Struct access: `struct.field`
- Array expansion: `explode()`
- Interval multiplication: `INTERVAL 1 HOUR * 2`

## Git Commit Messages
- Use imperative mood: "Add feature" not "Added feature"
- Be concise but descriptive
- Reference issues when applicable
- Examples:
  - "Fix dependency graph visualization with correct table name"
  - "Add PostgreSQL interval syntax for baseline queries"
  - "Remove OpenTelemetry instrumentation from codebase"
