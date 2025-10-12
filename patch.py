# patch.py
patches = [
    {
        "file": "prompt_foo.py",
        "block_name": "add_auto_context_method_body",
        "new_code": """
        # --- START DEBUGGING BLOCK ---
        condition = bool(content and "error" not in content.lower() and "skipping" not in content.lower())
        print(f"\\n[6] Inside add_auto_context for title '{title}': Condition to add is {condition}")
        # --- END DEBUGGING BLOCK ---
        if condition:
            self.auto_context[title] = {
                'content': content, 'tokens': count_tokens(content), 'words': count_words(content)
            }
        """
    },
    {
        "file": "prompt_foo.py",
        "block_name": "print_summary_body",
        "new_code": """
        # This method uses self.all_sections populated by build_final_prompt
        print("--- Files Included ---")
        for f in self.processed_files:
            if self.context_only:
                print(f"• {f['path']} (content omitted)")
            else:
                print(f"• {f['path']} ({f['tokens']:,} tokens)")
        
        if self.auto_context:
            print("\\n--- Auto-Context Included ---")
            for title, data in self.auto_context.items():
                print(f"• {title} ({data['tokens']:,} tokens)")

        print("\\n--- Prompt Summary ---")
        if self.context_only:
            print("NOTE: Running in --context-only mode. File contents are excluded.")

        total_tokens = sum(v.get('tokens', 0) for v in self.all_sections.values())
        total_words = sum(count_words(v.get('content', '')) for v in self.all_sections.values())

        print(f"Total Tokens: {total_tokens:,}")
        print(f"Total Words:  {total_words:,}")

        ratio = total_tokens / total_words if total_words > 0 else 0
        perspective = get_literary_perspective(total_words, ratio)
        print("\\n--- Size Perspective ---")
        print(perspective)
        print()
        """
    },
    {
        "file": "prompt_foo.py",
        "block_name": "main_post_argparse",
        "new_code": """
    # --- START DEBUGGING BLOCK ---
    print("\\n--- DEBUGGING OUTPUT ---")
    print(f"[1] Argument received by argparse for --list: {args.list!r}")
    # --- END DEBUGGING BLOCK ---

    if args.check_dependencies:
        check_dependencies()
        sys.exit(0)
        """
    },
    {
        "file": "prompt_foo.py",
        "block_name": "main_article_logic",
        "new_code": """
    print("Adding narrative context from articles...", end='', flush=True)
    all_articles = _get_article_list_data()
    
    # --- START DEBUGGING BLOCK ---
    print(f"\\n[2] Total articles found by _get_article_list_data(): {len(all_articles)}")
    # --- END DEBUGGING BLOCK ---

    sliced_articles = []
    try:
        slice_or_index = parse_slice_arg(args.list)

        # --- START DEBUGGING BLOCK ---
        print(f"[3] Parsed slice/index object: {slice_or_index!r}")
        # --- END DEBUGGING BLOCK ---
        
        if isinstance(slice_or_index, int): sliced_articles = [all_articles[slice_or_index]]
        elif isinstance(slice_or_index, slice): sliced_articles = all_articles[slice_or_index]
        
        # --- START DEBUGGING BLOCK ---
        print(f"[4] Length of article list AFTER slicing: {len(sliced_articles)}")
        # --- END DEBUGGING BLOCK ---

    except (ValueError, IndexError):
        print(f" (invalid slice '{args.list}')")
        sliced_articles = []
    
    if sliced_articles:
        narrative_content = "\\n".join(
            f"### {article['title']} ({article['date']})\\n> {article['summary']}\\n"
            for article in sliced_articles
        )
        # --- START DEBUGGING BLOCK ---
        print(f"\\n[5] Generated narrative_content length: {len(narrative_content)}")
        # --- END DEBUGGING BLOCK ---

        builder.add_auto_context("Recent Narrative Context", narrative_content)
        print(f" ({len(sliced_articles)} articles)")
    else:
        print(" (no articles found or invalid slice)")
        """
    },
    {
        "file": "prompt_foo.py",
        "block_name": "main_pre_summary",
        "new_code": """
    # --- START DEBUGGING BLOCK ---
    print("\\n--- MORE DEBUGGING ---")
    print(f"[7] Final auto_context keys before building prompt: {list(builder.auto_context.keys())}")
    print("--- END DEBUGGING ---\\n")
    # --- END DEBUGGING BLOCK ---

    # 4. Generate final output and print summary
    final_output = builder.build_final_prompt()
        """
    }
]