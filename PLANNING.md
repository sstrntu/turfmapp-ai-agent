# TURFMAPP AI Agent - Project Planning

## 🎯 Project Overview

TURFMAPP AI Agent is an intelligent chat application that provides AI-powered conversations with document upload capabilities, user management, and real-time chat functionality. The application follows a clean architecture pattern with separate backend and frontend services.

## 🏗️ Architecture & Technology Stack

### Backend Architecture
- **Framework**: FastAPI (Python 3.11+)
- **Database**: Supabase (PostgreSQL with pgvector)
- **Authentication**: Supabase Auth + JWT tokens
- **AI Integration**: OpenAI GPT models
- **Containerization**: Docker with docker-compose
- **Testing**: pytest with comprehensive coverage

### Frontend Architecture
**Current Implementation**: Dual approach (needs resolution)
- **Static HTML/JS**: Fully functional production app
- **React/Vite**: Incomplete implementation (requires completion)

**Target Stack** (per code.md):
- **Framework**: React 18+ with TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **State Management**: Zustand (recommended)
- **Testing**: Vitest + React Testing Library
- **Data Fetching**: TanStack Query

## 📁 Project Structure

### Backend Structure
```
backend/
├── app/
│   ├── api/v1/          # API routes (versioned)
│   │   ├── chat.py      # Chat endpoints (NEEDS REFACTOR)
│   │   ├── auth.py      # Authentication
│   │   ├── upload.py    # File uploads
│   │   └── preferences.py
│   ├── services/        # Business logic layer
│   │   ├── chat_service.py    # Chat operations
│   │   ├── user_service.py    # User management
│   │   └── conversation_service.py
│   ├── models/          # Pydantic models & SQLAlchemy
│   │   ├── auth.py      # Auth models
│   │   ├── user.py      # User models
│   │   └── conversation.py
│   ├── core/            # Core utilities
│   │   ├── auth.py      # Auth utilities
│   │   ├── config.py    # Configuration
│   │   └── database.py  # DB connection
│   ├── agents/          # AI agent system
│   │   └── routing/     # Agent routing (NEEDS INTEGRATION)
│   └── utils/           # Helper utilities
├── tests/              # Comprehensive test suite
├── requirements.txt    # Python dependencies
└── Dockerfile         # Container configuration
```

### Frontend Structure (Target)
```
frontend/
├── src/
│   ├── components/      # Reusable React components
│   │   ├── ui/         # Basic UI components
│   │   └── features/   # Feature-specific components
│   ├── pages/          # Route components
│   ├── lib/            # Utilities and hooks
│   ├── types/          # TypeScript definitions
│   └── styles/         # Global styles
├── public/             # Static assets
├── package.json
├── vite.config.ts
└── Dockerfile
```

## 🔧 Development Patterns

### Backend Patterns
- **Clean Architecture**: API → Service → Repository → Database
- **Dependency Injection**: FastAPI's built-in DI system
- **Error Handling**: Centralized exception handling
- **Type Safety**: Comprehensive type hints with Pydantic
- **Testing**: Unit tests for services, integration tests for API

### Frontend Patterns
- **Component Composition**: Small, reusable components
- **Custom Hooks**: Encapsulated logic in React hooks
- **Type Safety**: Strict TypeScript configuration
- **State Management**: Global state with Zustand, server state with TanStack Query

## 🎨 Design System

### Colors & Theming
- **Primary**: Custom DANSON font family
- **Style**: Glass morphism with backdrop blur
- **Colors**: White-based palette with transparency
- **Responsive**: Mobile-first approach

### Component Guidelines
- **Accessibility**: WCAG 2.1 AA compliance
- **Performance**: Code splitting and lazy loading
- **Consistency**: Shared component library
- **Documentation**: Storybook for component documentation

## 🔐 Security Considerations

### Backend Security
- **Authentication**: JWT tokens with proper expiration
- **Database**: Row-level security (RLS) with Supabase
- **API**: Rate limiting and input validation
- **CORS**: Configured for specific origins

### Frontend Security
- **API Integration**: Backend-as-proxy pattern (NO direct Supabase access)
- **Token Storage**: Secure token handling
- **Input Validation**: Client-side validation + server validation
- **XSS Prevention**: Proper sanitization

## 🧪 Testing Strategy

### Backend Testing
- **Unit Tests**: Service layer and utility functions
- **Integration Tests**: API endpoints with test database
- **Coverage Target**: >80% code coverage
- **Test Data**: Fixtures and factories for consistent test data

### Frontend Testing
- **Unit Tests**: Component testing with React Testing Library
- **Integration Tests**: User flow testing
- **E2E Tests**: Critical path testing with Playwright
- **Visual Testing**: Component visual regression tests

## 🚀 Deployment Strategy

### Development Environment
- **Docker Compose**: Local development with hot reload
- **Database**: Supabase for consistent development/production
- **Environment Variables**: .env files for configuration

### Production Deployment
- **Containerization**: Multi-stage Docker builds
- **Database**: Managed Supabase instance
- **CDN**: Static asset delivery
- **Monitoring**: Application performance monitoring

## 📊 Performance Goals

### Backend Performance
- **Response Time**: <200ms for API endpoints
- **Throughput**: 1000+ requests/second
- **Database**: Optimized queries with indexes
- **Caching**: Redis for frequently accessed data

### Frontend Performance
- **First Contentful Paint**: <1.5s
- **Time to Interactive**: <3s
- **Bundle Size**: <500KB initial load
- **Core Web Vitals**: All metrics in "Good" range

## 🔄 Development Workflow

### Code Quality
- **Formatting**: Black for Python, Prettier for TypeScript
- **Linting**: Flake8 for Python, ESLint for TypeScript
- **Type Checking**: mypy for Python, strict TypeScript
- **Pre-commit**: Automated quality checks

### Git Workflow
- **Branching**: Feature branches from main
- **Code Review**: Required for all changes
- **Testing**: Automated testing in CI/CD
- **Documentation**: Keep docs updated with changes

## 🎯 Current Development Priorities

### Immediate (This Week)
1. **Refactor chat.py** - Split into proper modules
2. **Create TASK.md** - Track development tasks
3. **Install frontend dependencies** - Fix UNMET DEPENDENCY issues
4. **Choose frontend architecture** - React or static HTML

### Short Term (Next 2 Weeks)
1. **Integrate agent routing system** - Connect to main application
2. **Implement proper service layer** - Use existing ChatService
3. **Set up frontend testing** - Vitest + React Testing Library
4. **Add Tailwind CSS** - If continuing with React approach

### Medium Term (Next Month)
1. **Performance optimization** - Database and API improvements
2. **Security hardening** - Rate limiting, input validation
3. **Comprehensive testing** - Reach 90%+ coverage
4. **Documentation** - API docs and user guides

## 📋 Code Quality Standards

### File Organization
- **Maximum file length**: 500 lines (currently violated by chat.py)
- **Single responsibility**: One concern per file
- **Clear naming**: Descriptive names for functions and variables
- **Documentation**: Docstrings for all public functions

### Architecture Principles
- **Separation of concerns**: Clear boundaries between layers
- **Dependency inversion**: High-level modules don't depend on low-level
- **Interface segregation**: Small, focused interfaces
- **Don't repeat yourself**: Shared utilities for common functionality

This planning document will be updated as the project evolves and new requirements emerge.