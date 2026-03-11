# Project Evolution Plan: WhatsApp AI Bot with Multi-Tenant Dashboard

**Last Updated:** March 10, 2026

---

## 1. Current State Analysis

### What's Already There ✅

| Component | Status | Files |
|-----------|--------|-------|
| FastAPI server | ✅ Webhooks, Google Drive OAuth | `main.py` |
| WhatsApp bot | ✅ Text, voice, image, document handling | `message_processor.py`, `twilio_client.py` |
| Claude agent | ✅ RAG, Google Drive tools | `roleplay_agent.py`, `tools.py` |
| Knowledge base | ✅ Pinecone vector search | `pinecone_client.py` |
| Chat history | ✅ Redis-based | `chat_history_manager.py` |
| File storage | ✅ Cloudinary + Supabase Storage | `supabase_storage.py`, `cloudinary_storage.py` |

### What's Missing ❌

| Feature | Priority |
|---------|----------|
| Authentication (login/signup) | HIGH |
| Organization management | HIGH |
| User management (dashboard) | HIGH |
| Role management (custom roles) | HIGH |
| WhatsApp-user mapping | HIGH |
| Role-based query restrictions | MEDIUM |
| Frontend (landing + dashboard) | HIGH |

---

## 2. Technology Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI (existing) + PostgreSQL |
| ORM | SQLAlchemy 2.0 + Pydantic |
| Auth | JWT (python-jose) + Password hashing (bcrypt) |
| Frontend | FastAPI Templates (Jinja2) + HTMX |
| Database | PostgreSQL (via Docker) |
| WhatsApp | Twilio (existing) |

---

## 3. Database Schema

### 3.1 Tables

```sql
-- Organizations (multi-tenant)
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    owner_id UUID REFERENCES users(id),
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Users (auth)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Profiles (org-specific user info)
CREATE TABLE profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    username VARCHAR(255),
    whatsapp_number VARCHAR(50),
    role_id UUID REFERENCES roles(id),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, org_id)
);

-- Roles (custom per org)
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    permissions JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Documents
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255),
    drive_file_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 3.2 Permissions Schema (JSON)

```json
{
  "query:financial": true,
  "query:strategic": true,
  "query:sensitive": false,
  "document:read": true,
  "document:upload": true,
  "user:manage": false
}
```

---

## 4. API Endpoints

### 4.1 Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/signup` | Create org + admin user |
| POST | `/auth/login` | Login → JWT token |
| POST | `/auth/logout` | Invalidate session |
| GET | `/auth/me` | Get current user |

### 4.2 Organizations
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/orgs/{id}` | Get org details |
| PUT | `/api/orgs/{id}` | Update org settings |

### 4.3 Users (Dashboard)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/users` | List users in org |
| POST | `/api/users` | Add new user |
| PUT | `/api/users/{id}` | Update user |
| DELETE | `/api/users/{id}` | Revoke access (deactivate) |
| POST | `/api/users/{id}/reactivate` | Re-enable access |

### 4.4 Roles
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/roles` | List roles in org |
| POST | `/api/roles` | Create custom role |
| PUT | `/api/roles/{id}` | Update role permissions |
| DELETE | `/api/roles/{id}` | Delete role |

### 4.5 Documents
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/documents` | List documents |
| POST | `/api/documents` | Add document reference |

---

## 5. Frontend Pages (FastAPI Templates)

### 5.1 Route Structure

| Route | Template | Description |
|-------|----------|-------------|
| `/` | `index.html` | Landing page |
| `/login` | `login.html` | Login form |
| `/signup` | `signup.html` | Signup form (creates org) |
| `/dashboard` | `dashboard.html` | Main dashboard |
| `/dashboard/users` | `users.html` | User management |
| `/dashboard/documents` | `documents.html` | Document list |
| `/dashboard/settings` | `settings.html` | Org settings |

### 5.2 Sidebar Navigation

```
┌─────────────────────┐
│  📊 Dashboard       │
│  👥 Users           │
│  📄 Documents       │
│  ⚙️ Settings        │
└─────────────────────┘
```

### 5.3 Add User Modal

Fields:
- Username (text)
- WhatsApp Number (text with validation)
- Role (dropdown from org's roles)

---

## 6. WhatsApp Bot Enhancement

### 6.1 User Lookup Flow

```
Incoming WhatsApp message
         │
         ▼
Extract phone number from Twilio
         │
         ▼
Lookup in profiles table by whatsapp_number
         │
    ┌────┴────┐
    │ Found?  │
    └────┬────┘
     No  │  Yes
     │   │  ┌──────────────┐
     ▼   │  │ Check        │
 "No access"│ is_active    │
 message    └────┬──────────┘
              ┌──┴──┐
              │Yes  │ No
              ▼     ▼
         Get role  "Access
         + org     revoked"
              │
              ▼
    Store in Redis for
    session context
```

### 6.2 AI-Powered Query Classification

Before responding to any query:

1. **Classify the query** using Claude:
   - `financial` - budget, revenue, costs, salaries
   - `strategic` - CEO/CFO level, roadmap, M&A
   - `sensitive` - personal, confidential
   - `general` - everything else

2. **Check user permissions**:
   - If user's role has `query:{type}: true` → allow
   - If `false` → block with message

3. **Example blocked response**:
   > "I apologize, but this query is beyond your access level. Please contact your administrator for more information."

---

## 7. Implementation Phases

### Phase 1: Backend Foundation (Week 1)
- [ ] Set up PostgreSQL with SQLAlchemy
- [ ] Create database models
- [ ] Implement auth endpoints (signup, login, JWT)
- [ ] Create organization on signup

### Phase 2: User & Role Management (Week 1-2)
- [ ] CRUD endpoints for users
- [ ] CRUD endpoints for roles
- [ ] WhatsApp number mapping in profiles
- [ ] Default roles on org creation (Admin, Manager, Employee, Intern)

### Phase 3: WhatsApp Bot Integration (Week 2)
- [ ] Add org/user lookup in webhook
- [ ] Implement query classification
- [ ] Add permission checking before responding
- [ ] Block restricted queries

### Phase 4: Frontend (Week 2-3)
- [ ] Create base template with sidebar
- [ ] Landing page
- [ ] Login/Signup pages
- [ ] Dashboard with stats
- [ ] Users page with Add User modal
- [ ] Documents page
- [ ] Settings page

### Phase 5: Integration & Polish (Week 3)
- [ ] Connect frontend to backend APIs
- [ ] Test role restrictions end-to-end
- [ ] Document upload flow
- [ ] Testing and bug fixes

---

## 8. File Structure

```
agente_rolplay/
├── src/agente_rolplay/
│   ├── main.py                    # FastAPI app (existing)
│   ├── database.py                # NEW: SQLAlchemy setup
│   ├── models.py                  # NEW: Database models
│   ├── schemas.py                 # NEW: Pydantic schemas
│   ├── auth.py                    # NEW: Auth utilities
│   ├── routers/                   # NEW: API routers
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── roles.py
│   │   ├── documents.py
│   │   └── orgs.py
│   ├── templates/                 # NEW: Jinja2 templates
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── login.html
│   │   ├── signup.html
│   │   ├── dashboard.html
│   │   ├── users.html
│   │   ├── documents.html
│   │   └── settings.html
│   └── static/                    # NEW: CSS, JS
│       ├── css/styles.css
│       └── js/htmx.min.js
├── scripts/
│   └── init_db.py                 # NEW: Database initialization
├── docker-compose.yml             # (existing)
└── pyproject.toml                 # (add dependencies)
```

---

## 9. Dependencies to Add

```toml
# pyproject.toml additions
sqlalchemy = ">=2.0"
psycopg2-binary = ">=2.9"
python-jose = ">=3.3"
passlib = ">=1.7"
bcrypt = ">=4.0"
python-multipart = ">=0.0"
jinja2 = ">=3.1"
```

---

## 10. Next Steps

1. Start Phase 1: Backend Foundation
2. Set up PostgreSQL with SQLAlchemy
