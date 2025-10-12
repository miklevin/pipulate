# patch.py
patches = [
    {
        "file": "prompt_foo.py",
        "block_name": "add_auto_context_method_body",
        "new_code": """
        is_narrative = (title == "Recent Narrative Context")
        content_is_valid = bool(content)
        filter_passed = "error" not in content.lower() and "skipping" not in content.lower()

        # The narrative context should always be added if it exists.
        # Other contexts should be filtered to avoid including script errors.
        if content_is_valid and (is_narrative or filter_passed):
            self.auto_context[title] = {
                'content': content, 'tokens': count_tokens(content), 'words': count_words(content)
            }
        """
    }
]