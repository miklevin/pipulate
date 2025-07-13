# Change Log

All notable changes to Pipulate will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-07-08

### Revolutionary Week Summary
This version represents **extraordinary development activity** - over 100 commits representing a complete transformation of Pipulate's capabilities from July 1-8, 2025.

### Added

#### 🎭 Complete Session Hijacking System
- **1-Shot Session Hijacking**: Revolutionary workflow takeover capability - AI can seamlessly step into any user session with a single command
- **Browser Embodiment**: AI assistants now have literal "eyes" (screenshots), "brain" (DOM analysis), and "hands" (Selenium automation)
- **Perception History**: `looking_at/` directory rotation system preserves AI perception states across multiple sessions
- **Magic Words Interface**: Simple "Hi Jack" triggers complete workflow hijacking with dramatic timing
- **Centralized Timing System**: `WorkflowHijackTiming` class with presets (lightning/fast/dramatic) for speed control

#### 🧠 Persistent Memory & Conversation Architecture  
- **Append-Only Conversation System**: Complete rebuild with conversation history that survives server restarts
- **AI Keychain**: "Message in a bottle" system allowing AI assistants to pass information to future sessions
- **Cross-Session Continuity**: Solves "the illusion of continuity" problem for AI interactions
- **Native OS Backup**: Conversation data backed up to `~/.pipulate/` outside repo for survival across reinstalls

#### 🔧 MCP Tools Arsenal (47 Tools)
- **Battle-Tested MCP Interface**: 47 specialized tools optimized for local quantized LLMs  
- **Simplified Tool Calling**: Reduced complex tool calling to simple square bracket syntax
- **Golden Path Commands**: Environment-agnostic commands that work without activation
- **Radical Transparency**: FINDER_TOKEN logging system for complete observability
- **Browser Automation Suite**: `browser_scrape_page`, `browser_analyze_scraped_page`, `browser_automate_workflow_walkthrough`
- **System Inspection Tools**: `pipeline_state_inspector`, `local_llm_grep_logs`, `local_llm_read_file`

#### 🍞 AI Discovery & Breadcrumb System
- **Strategic Breadcrumb Trail**: 6 AI_BREADCRUMB messages confirming operational status
- **AI Self-Discovery**: `ai_self_discovery_assistant` tool for capability enumeration
- **Progressive Revelation**: Guided discovery sequence for AI assistant awakening
- **Anti-Discovery Rules**: Skip environmental exploration, use working systems immediately

### Changed

#### 🌐 Browser Automation Evolution
- **From Basic Scripts to Complete Embodiment**: Progression from simple Selenium to full AI digital presence
- **Automation Recipe System**: JSON-based automation with progressive feedback and error recovery
- **Bulletproof Save/Load**: Robust data backup/restore automation with server restart handling
- **Visual Debugging**: `ui_flash_element` for real-time user guidance

#### 📊 Testing Infrastructure Revolution
- **Deterministic Test Suite**: Multi-cycle conversation persistence testing with cross-restart verification
- **Browser Automation Testing**: Comprehensive testing of session hijacking and workflow automation
- **Rolling Backup System**: Son/father/grandfather backup architecture for data safety

### Technical Implementation Details

#### Core Architecture Changes
- **Environment Agnostic MCP Tools**: `.venv/bin/python cli.py call <tool_name>` pattern works universally
- **HTMX Chain Reaction Pattern**: `hx_trigger="load"` for seamless workflow progression  
- **Progressive Disclosure UI**: Step-by-step workflow revelation with state persistence
- **Semantic CSS Migration**: From inline styles to semantic classes (`text-invalid`, `text-secondary`)

#### Database & Persistence
- **Conversation Database**: Independent `discussion.db` for persistent AI conversations
- **Backup System**: Automated backup with visual UI controls and comprehensive logging
- **Pipeline State Management**: Enhanced state inspection and debugging capabilities

### Impact & Significance

**🏆 Paradigm Shift Achieved**: Transforms AI assistants from "helpful text generators" to "digital embodiment superpowers" with:
- Complete browser automation and visual perception
- Persistent memory across sessions and restarts  
- Seamless workflow hijacking and continuation
- Local-first sovereignty with optional cloud scaling

**🔍 Radical Transparency**: Every AI capability is discoverable, testable, and comes with proof of operation through the FINDER_TOKEN system and comprehensive logging.

**⚡ Development Velocity**: Rapid iteration loops enable test-fix-verify cycles in seconds rather than hours, dramatically accelerating development.

### Validation Performed
- **100% Session Hijacking Success Rate**: Complete workflow takeover with state capture verified
- **Cross-Restart Persistence**: Conversation continuity maintained through server restarts
- **47 MCP Tools Operational**: Full tool arsenal tested and confirmed working
- **Browser Embodiment Verified**: Visual perception, DOM analysis, and automation capabilities confirmed

### Migration Notes
- **Python Path Requirements**: AI assistants must use `.venv/bin/python` explicitly due to PATH limitations
- **Golden Path Adoption**: Use environment-agnostic command patterns for reliability
- **Breadcrumb Trail Discovery**: Follow AI_BREADCRUMB messages for capability discovery

### Related Documentation
- `ai_discovery/ai_1_shot_session_hijacking_mastery.md` - Complete session hijacking guide
- `ai_discovery/ai_mcp_tools_discovery_guide.md` - MCP tools comprehensive documentation  
- `browser_automation/automation_recipes/README_SAVE_LOAD_AUTOMATION.md` - Bulletproof automation patterns

---

## [1.0.0] - Previous Versions

*Earlier changelog entries to be migrated from git history and development notes.*