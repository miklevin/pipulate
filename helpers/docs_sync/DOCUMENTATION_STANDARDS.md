# 📚 Pipulate Documentation Organization Standards

## 🎯 Purpose
This document establishes clear organizational standards for documentation across the Pipulate repository, ensuring consistency, discoverability, and historical preservation.

## 📁 Documentation Hierarchy

### **Primary Documentation Locations**

```
pipulate/
├── README.md                              # Main repository overview (STAYS IN ROOT)
├── training/                              # LLM workflow training prompts (STABLE)
├── helpers/docs_sync/                     # Milestone & consideration documentation
│   ├── considerations/                    # Timestamped milestone documentation
│   └── DOCUMENTATION_STANDARDS.md        # This file
└── ai_discovery/                          # AI assistant onboarding guides
```

### **Specialized Documentation Areas**

- **`training/`** - Workflow-specific LLM training prompts (clear domain boundary)
- **`helpers/docs_sync/`** - Exposed via Documentation plugin to users
- **`ai_discovery/`** - AI assistant discovery and onboarding materials
- **`branches/`** - Branch-specific documentation (if needed)

## 🏷️ Naming Conventions

### **Milestone Documentation** (in `helpers/docs_sync/considerations/`)
```
YYYY-MM-DD-descriptive-title-in-kebab-case.md
```

**Examples:**
- `2025-07-21-lightning-in-a-bottle-insights.md`
- `2025-07-21-demo-continuation-system-fully-working.md`
- `2025-07-21-nuclear-safety-absolute-protection.md`

### **Required Timestamp Format**
All milestone documentation MUST include:
```markdown
---
created: YYYY-MM-DD
milestone: Brief description of achievement
status: active|archived|superseded
---
```

## 📋 Documentation Categories

### **1. Milestone Documentation** (`helpers/docs_sync/considerations/`)
- **Purpose**: Record significant achievements, breakthroughs, and system changes
- **Naming**: `YYYY-MM-DD-milestone-description.md`
- **Retention**: Permanent historical record
- **Review**: Compare against codebase for accuracy over time

### **2. Training Prompts** (`training/`)
- **Purpose**: LLM workflow training and just-in-time prompt injection
- **Naming**: `workflow_name.md`
- **Retention**: Stable, version-controlled
- **Review**: Updated with workflow changes

### **3. AI Discovery** (`ai_discovery/`)
- **Purpose**: AI assistant onboarding and capability discovery
- **Naming**: `ai_topic_guide.md`
- **Retention**: Living documents, updated as capabilities evolve
- **Review**: Regular updates for AI assistant effectiveness

### **4. Living Documentation** (`helpers/docs_sync/`)
- **Purpose**: User-exposed documentation via Documentation plugin
- **Naming**: Descriptive titles
- **Retention**: Maintained as long as relevant
- **Review**: User-focused accuracy

## 🔄 Lifecycle Management

### **Documentation Flow**
```
Creation → Timestamping → Categorization → Review Cycles → Archive/Update
```

### **Review Cycles**
- **Monthly**: Check milestone docs against current codebase reality
- **Quarterly**: Archive superseded documentation
- **Semi-annual**: Distill learnings into training prompts or stable docs

### **Migration Process**
When moving documentation:
1. Use `git mv` to preserve repository history
2. Add appropriate timestamp prefix
3. Update internal references
4. Commit with descriptive message

## 🎯 Quality Standards

### **All Documentation Must Include:**
- **Timestamp**: When created/last updated
- **Purpose**: Why this document exists
- **Context**: What problem it solves or milestone it records
- **Status**: Current relevance (active/archived/superseded)

### **Milestone Documentation Must Include:**
- **Achievement Summary**: What was accomplished
- **Technical Details**: Key implementation notes
- **Code References**: Specific files/functions involved
- **Historical Context**: Why this was significant

## 🚀 Implementation Guidelines

### **For New Milestone Documentation:**
```bash
# Use current date timestamp
TODAY=$(date +%Y-%m-%d)
touch "helpers/docs_sync/considerations/${TODAY}-new-milestone-title.md"
```

### **For Moving Existing Documentation:**
```bash
# Preserve git history
git mv OLD_FILE.md "helpers/docs_sync/considerations/YYYY-MM-DD-new-name.md"
```

### **Commit Message Format:**
```
📚 DOCS: Brief description of documentation change

Details:
- What was moved/created
- Why the change was made
- Any organizational improvements
```

## 📈 Benefits of This System

- **Historical Preservation**: Timestamped milestones create permanent record
- **Discoverability**: Clear categorization and naming conventions
- **User Exposure**: docs_sync content accessible via Documentation plugin
- **AI Integration**: ai_discovery guides AI assistant onboarding
- **Codebase Alignment**: Regular review ensures accuracy over time
- **Repository History**: git mv preserves valuable commit history

## 🎭 Special Note: Lightning in a Bottle

This documentation system was established during the "Lightning in a Bottle" achievement (commit `21af293`) - the breakthrough that solved bulletproof demo continuation across server restarts. This milestone demonstrates why proper documentation organization is crucial for preserving breakthrough insights.

---

**Created**: 2025-07-21  
**Milestone**: Documentation organization standards established  
**Status**: Active foundational document 