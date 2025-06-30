---
title: "The Living README Revolution: Parsable ASCII Art Dictionary System"
---

What if your README.md could be more than just documentation? What if every ASCII art diagram could be a **parsable, distributable asset** that maintains consistency across your entire project?

The Living README system transforms documentation from static text into a **dynamic source of truth** where visual elements become first-class citizens in your documentation ecosystem.

### The Parsing Strategy

Each ASCII art block follows a structured format that enables automatic extraction and distribution:

```
### Headline (becomes the title/key)
Header content
```
ASCII art content
```
Footer content
```

### The Distribution Revolution

**Source**: README.md (clean, beautiful, GitHub-friendly)  
**Destinations**: Any .md/.mdc file with markers

This creates a "foolproof failsafe" single source of truth for all ASCII art across the entire Pipulate ecosystem, enabling documentation that writes itself.

---

*This post outlines the Living README implementation strategy. See the [Pipulate project](https://github.com/miklevin/pipulate) for the complete documentation system.* 