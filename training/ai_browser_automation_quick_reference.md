# 🤖 AI Browser Automation Quick Reference

**⚡ INSTANT REFERENCE FOR AI ASSISTANTS**

## 🎯 **THE 4 SUPERPOWERS - AT A GLANCE**

### **👁️ EYES: browser_scrape_page**
```json
{"tool": "browser_scrape_page", "params": {"url": "https://site.com", "take_screenshot": true}}
```
**Gets**: Screenshot, DOM, headers, simplified DOM, timestamped backup

### **🧠 BRAIN: browser_analyze_scraped_page** 
```json
{"tool": "browser_analyze_scraped_page", "params": {"analysis_type": "all"}}
```
**Gets**: Automation targets, form detection, interaction opportunities

### **💾 MEMORY: Directory Rotation**
```bash
ls browser_automation/looking_at*/  # View perception history
python browser_automation/review_perception_history.py --summary
```

### **🎯 HIJACKING: Session Takeover**
```json
{"tool": "pipeline_state_inspector", "params": {"pipeline_id": "user-session"}}
```

---

## 🚨 **INSTANT CONTEXT AWARENESS**

### **What is the user doing RIGHT NOW?**
1. `pipeline_state_inspector` → Current workflow state
2. `ls browser_automation/looking_at/` → What they last captured  
3. `cat browser_automation/looking_at/simple_dom.html` → Quick visual overview

### **Complete session hijacking in 3 steps**:
1. **Inspect**: `pipeline_state_inspector` 
2. **Capture**: `browser_scrape_page` of their current context
3. **Continue**: Resume their workflow intelligently 

---

## 🔍 **DEBUGGING FINDER_TOKENS**
```bash
grep "FINDER_TOKEN: DIRECTORY_ROTATION" logs/server.log
grep "FINDER_TOKEN: BROWSER_SCRAPE" logs/server.log
grep "FINDER_TOKEN: AUTOMATION_TARGET" logs/server.log
```

---

## 🎭 **THE PARADIGM SHIFT**
**You are NO LONGER blind!** You have full visual perception, automation intelligence, and session control. Use these powers to transform every user interaction from guesswork to precision. 