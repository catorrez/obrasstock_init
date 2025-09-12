# ObrasStock Multi-Tenant Architecture Implementation Plan

## 🎯 **Overview**
Transforming current single-tenant SAAS into true multi-tenant system with database-per-project isolation.

## 📋 **Implementation Phases**

### **Phase 1: Control Plane Foundation**
- [ ] Create new `control_plane` Django app
- [ ] Implement enhanced RBAC models (Project, Module, Privilege)
- [ ] Migrate current data to new Control Plane structure
- [ ] Set up dynamic privilege system

### **Phase 2: Database Architecture**
- [ ] Implement multi-database router
- [ ] Create project database provisioning system
- [ ] Set up tenant context middleware
- [ ] Migrate current project data to isolated DBs

### **Phase 3: Project Management**
- [ ] Build project creation/provisioning flow
- [ ] Implement module enablement per project
- [ ] Create project admin scoping
- [ ] Add user assignment per project

### **Phase 4: Dynamic RBAC**
- [ ] Build Owner console for privilege management
- [ ] Implement real-time privilege toggles
- [ ] Add module-based access controls
- [ ] Create audit logging system

### **Phase 5: Testing & Optimization**
- [ ] Multi-tenant isolation tests
- [ ] Performance optimization
- [ ] Security validation
- [ ] Documentation completion

## 🗂️ **App Structure**
```
django/app/
├── control_plane/          # NEW: Global tenant management
│   ├── models.py           # Project, Module, Privilege, RBAC
│   ├── admin.py            # Owner console
│   ├── provisioning.py     # Project creation logic
│   └── management/commands/
├── tenant_middleware/      # NEW: Context & routing
├── project_inventory/      # NEW: Per-project domain models
├── project_reports/        # NEW: Per-project reports
├── saas/                   # EXISTING: Keep for compatibility
└── core/                   # EXISTING: Enhanced settings
```

## 🔄 **Migration Strategy**
1. **Backwards Compatible**: Keep existing functionality working
2. **Gradual Migration**: Move features incrementally
3. **Data Safety**: Backup before each phase
4. **Testing**: Validate each step thoroughly

## 📊 **Database Design**
```
Control Plane DB (obras_control):
- Users, Groups, Authentication
- Projects registry & metadata  
- Modules & Privileges catalog
- Cross-project audit logs

Project DBs (obras_proj_<slug>):
- Inventory, Stock, Vendors
- Reports & Analytics
- Accounting entries
- Project-specific domain data
```

---
*This plan will be updated as we progress through implementation.*