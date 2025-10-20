# Bug Fix: Filename Sanitization in Claude Export Parser

## Problem

The `claude_export_parser.py` script was crashing with a `FileNotFoundError` when trying to export code blocks that had invalid filenames extracted from their content. 

**Error Message:**
```
FileNotFoundError: [Errno 2] No such file or directory: "scripts/import { defineConfig } from 'vitest/config';"
```

## Root Cause

The parser was using the first line of code blocks as filenames when no explicit filename was provided. Lines like:
- `import { defineConfig } from 'vite';`
- `## File Contents`
- `### tsconfig.json`

These contain special characters (spaces, braces, semicolons, slashes) that are invalid in filenames and were causing the file system operations to fail.

## Solution

Added a `_sanitize_filename()` method that:

1. **Removes invalid characters** - Replaces anything that's not alphanumeric, dot, dash, or underscore with underscores
2. **Strips problematic prefixes/suffixes** - Removes leading/trailing dots, dashes, underscores
3. **Ensures non-empty filenames** - Falls back to `untitled.{ext}` if sanitization results in empty string
4. **Enforces extensions** - Adds appropriate file extension if missing
5. **Limits length** - Truncates to 100 characters while preserving the extension

### Code Changes

```python
def _sanitize_filename(self, filename: str, fallback_ext: str = 'txt') -> str:
    """Sanitize filename to remove invalid characters and enforce reasonable length."""
    # Remove or replace invalid characters
    # Keep only alphanumeric, dots, dashes, underscores
    sanitized = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    
    # Remove leading/trailing dots, dashes, underscores
    sanitized = sanitized.strip('._-')
    
    # Ensure it's not empty
    if not sanitized:
        sanitized = f'untitled.{fallback_ext}'
    
    # Ensure it has an extension
    if '.' not in sanitized:
        sanitized = f'{sanitized}.{fallback_ext}'
    
    # Limit length (keep extension)
    if len(sanitized) > 100:
        parts = sanitized.rsplit('.', 1)
        name = parts[0][:95]
        ext = parts[1] if len(parts) > 1 else fallback_ext
        sanitized = f'{name}.{ext}'
    
    return sanitized
```

Modified the `export_scripts()` method to use sanitization:

```python
if code_block.filename:
    # Sanitize the provided filename
    ext = self._get_extension(code_block.language)
    filename = self._sanitize_filename(code_block.filename, ext)
```

## Results

After the fix:
- ✅ Parser completes successfully
- ✅ Extracted 6 artifacts to proper paths (`.github/workflows/`, etc.)
- ✅ Exported 66 code blocks with sanitized filenames
- ✅ Generated 59 documentation files

### Example Sanitized Filenames

| Original | Sanitized |
|----------|-----------|
| `import { defineConfig } from 'vite';` | `import___defineConfig___from__vite.ts` |
| `## File Contents` | `File_Contents.txt` |
| `### tsconfig.json` | `tsconfig.json` |
| `User → React Component → urql Query` | `User___React_Component___urql_Query___Hasura_GraphQL___PostgreSQL.txt` |

## Testing

Tested with `fiction-index.md` export containing:
- Complex TypeScript imports
- Markdown headers as code block titles
- Special characters in documentation
- Multi-language code blocks

All files now export successfully to the `scripts/` directory.

## Future Improvements

Consider:
1. Better filename inference from code content (e.g., extract actual filenames from comments)
2. Option to use hash-based filenames for truly unidentifiable code blocks
3. Collision detection with semantic suffixes (not just numbers)
4. Language-specific filename patterns (e.g., React components as `ComponentName.tsx`)

## Files Modified

- `claude-exporter/claude_export_parser.py` - Added `_sanitize_filename()` method and updated `export_scripts()`

## Date

October 20, 2025
