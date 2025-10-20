#!/usr/bin/env python3
"""
Claude Conversation Export Parser
Parses exported Claude conversation markdown files and organizes content into directories.
"""

import re
import os
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Artifact:
    """Represents an artifact from the conversation."""
    title: str
    content: str
    path: Optional[str] = None
    language: Optional[str] = None


@dataclass
class CodeBlock:
    """Represents a code block from the conversation."""
    content: str
    language: str
    filename: Optional[str] = None


@dataclass
class Response:
    """Represents a response section from Claude."""
    content: str
    timestamp: Optional[datetime] = None


class ConversationParser:
    """Parser for Claude conversation export files."""
    
    # Regex patterns
    ARTIFACT_PATTERN = re.compile(
        r'```(?P<lang>\w+)\s*\n'
        r'(?P<content>.*?)'
        r'\n```',
        re.DOTALL
    )
    
    CODE_BLOCK_PATTERN = re.compile(
        r'```(?P<lang>\w+)?(?:\s+(?P<filename>[^\n]+))?\s*\n'
        r'(?P<content>.*?)'
        r'\n```',
        re.DOTALL
    )
    
    METADATA_PATTERN = re.compile(
        r'\*\*(?P<key>Created|Updated|Exported):\*\*\s+(?P<value>[^\n]+)'
    )
    
    TITLE_PATTERN = re.compile(r'^#\s+(.+)$', re.MULTILINE)
    
    def __init__(self, filepath: str | Path):
        """Initialize parser with a file path."""
        self.filepath = Path(filepath)
        self.content = self.filepath.read_text(encoding='utf-8')
        self.artifacts: List[Artifact] = []
        self.code_blocks: List[CodeBlock] = []
        self.responses: List[Response] = []
        self.metadata: Dict[str, str] = {}
        
    def parse(self) -> None:
        """Parse the conversation file."""
        self._extract_metadata()
        self._extract_artifacts()
        self._extract_code_blocks()
        self._extract_responses()
        
    def _extract_metadata(self) -> None:
        """Extract metadata from the file."""
        for match in self.METADATA_PATTERN.finditer(self.content):
            key = match.group('key').lower()
            value = match.group('value').strip()
            self.metadata[key] = value
            
    def _extract_artifacts(self) -> None:
        """Extract artifacts with embedded file paths."""
        lines = self.content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Look for artifact headers like "## src/components/BookCard.tsx"
            if line.startswith('##') and '/' in line:
                # Extract path from header
                path_match = re.search(r'##\s+(.+?)(?:\s+-\s+.+)?$', line)
                if path_match:
                    path = path_match.group(1).strip()
                    
                    # Look ahead for code block
                    j = i + 1
                    while j < len(lines) and not lines[j].strip().startswith('```'):
                        j += 1
                    
                    if j < len(lines):
                        # Extract the code block
                        code_start = j
                        lang_line = lines[code_start].strip()
                        lang = lang_line.replace('```', '').strip() or 'text'
                        
                        j += 1
                        code_lines: list[str] = []
                        while j < len(lines) and not lines[j].strip().startswith('```'):
                            code_lines.append(lines[j])
                            j += 1
                        
                        content = '\n'.join(code_lines)
                        
                        # Infer title from path
                        title = Path(path).name
                        
                        self.artifacts.append(Artifact(
                            title=title,
                            content=content,
                            path=path,
                            language=lang
                        ))
                        
                        i = j + 1
                        continue
            
            i += 1
    
    def _extract_code_blocks(self) -> None:
        """Extract standalone code blocks not part of artifacts."""
        artifact_contents = {a.content for a in self.artifacts}
        
        for match in self.CODE_BLOCK_PATTERN.finditer(self.content):
            content = match.group('content')
            
            # Skip if already captured as artifact
            if content in artifact_contents:
                continue
                
            lang = match.group('lang') or 'text'
            filename = match.group('filename')
            
            # Infer filename from language if not provided
            if not filename:
                filename = self._infer_filename(content, lang)
            
            self.code_blocks.append(CodeBlock(
                content=content,
                language=lang,
                filename=filename
            ))
    
    def _extract_responses(self) -> None:
        """Extract markdown responses from Claude."""
        # Split content by code blocks and artifacts
        splits = re.split(r'```[\w\s]*\n.*?\n```', self.content, flags=re.DOTALL)
        
        for split in splits:
            # Clean up the split
            cleaned = split.strip()
            
            # Skip empty or very short splits
            if len(cleaned) < 50:
                continue
            
            # Skip metadata sections
            if any(key in cleaned for key in ['**Created:**', '**Updated:**', '**Exported:**']):
                continue
            
            # Skip if it's mostly code indicators
            if cleaned.count('```') > 2:
                continue
            
            self.responses.append(Response(content=cleaned))
    
    def _infer_filename(self, content: str, language: str) -> Optional[str]:
        """Infer a filename from code content and language."""
        # Check for shebang
        if content.startswith('#!'):
            first_line = content.split('\n')[0]
            if 'python' in first_line:
                return 'script.py'
            elif 'bash' in first_line or 'sh' in first_line:
                return 'script.sh'
        
        # Check for language-specific patterns
        if language in ('python', 'py'):
            # Look for class or function definitions
            if 'class ' in content:
                match = re.search(r'class\s+(\w+)', content)
                if match:
                    return f"{self._to_snake_case(match.group(1))}.py"
            if 'def ' in content:
                match = re.search(r'def\s+(\w+)', content)
                if match:
                    return f"{match.group(1)}.py"
            return 'script.py'
        
        elif language in ('javascript', 'js', 'typescript', 'ts'):
            # Look for class, function, or const definitions
            if 'class ' in content:
                match = re.search(r'class\s+(\w+)', content)
                if match:
                    return f"{match.group(1)}.{language}"
            if 'export ' in content:
                match = re.search(r'export\s+(?:default\s+)?(?:function|const)\s+(\w+)', content)
                if match:
                    return f"{match.group(1)}.{language}"
            ext = 'ts' if language in ('typescript', 'ts') else 'js'
            return f'script.{ext}'
        
        elif language in ('bash', 'sh', 'shell'):
            return 'script.sh'
        
        elif language == 'sql':
            return 'query.sql'
        
        elif language in ('yaml', 'yml'):
            return 'config.yml'
        
        elif language == 'json':
            return 'data.json'
        
        return None
    
    def _to_snake_case(self, name: str) -> str:
        """Convert CamelCase to snake_case."""
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    
    def _to_kebab_case(self, text: str) -> str:
        """Convert text to kebab-case."""
        # Remove special characters
        text = re.sub(r'[^\w\s-]', '', text)
        # Replace whitespace with hyphens
        text = re.sub(r'[\s_]+', '-', text)
        # Convert to lowercase
        return text.lower().strip('-')
    
    def export_artifacts(self, base_dir: str | Path) -> None:
        """Export artifacts to their specified paths."""
        base_dir = Path(base_dir)
        
        for artifact in self.artifacts:
            if artifact.path:
                filepath = base_dir / artifact.path
            else:
                # Fallback to artifacts directory
                filepath = base_dir / 'artifacts' / artifact.title
            
            # Create parent directories
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            # Write content
            filepath.write_text(artifact.content, encoding='utf-8')
            print(f"Exported artifact: {filepath}")
    
    def export_scripts(self, scripts_dir: str | Path) -> None:
        """Export code blocks to scripts directory."""
        scripts_dir = Path(scripts_dir)
        scripts_dir.mkdir(parents=True, exist_ok=True)
        
        for i, code_block in enumerate(self.code_blocks):
            # Determine filename
            if code_block.filename:
                filename = code_block.filename
            else:
                # Use language-based naming
                ext = self._get_extension(code_block.language)
                if code_block.language in ('bash', 'sh', 'shell'):
                    filename = f'script-{i+1}.sh'
                elif code_block.language in ('python', 'py'):
                    filename = f'script_{i+1}.py'
                else:
                    filename = f'script-{i+1}.{ext}'
            
            filepath = scripts_dir / filename
            
            # Avoid overwriting by appending number
            counter = 1
            while filepath.exists():
                stem = filepath.stem
                suffix = filepath.suffix
                filepath = scripts_dir / f"{stem}_{counter}{suffix}"
                counter += 1
            
            filepath.write_text(code_block.content, encoding='utf-8')
            
            # Make shell scripts executable
            if code_block.language in ('bash', 'sh', 'shell'):
                os.chmod(filepath, 0o755)
            
            print(f"Exported script: {filepath}")
    
    def export_docs(self, docs_dir: str | Path) -> None:
        """Export markdown responses to docs directory."""
        docs_dir = Path(docs_dir)
        docs_dir.mkdir(parents=True, exist_ok=True)
        
        for i, response in enumerate(self.responses):
            # Generate filename from content
            # Try to extract a title
            title_match = self.TITLE_PATTERN.search(response.content)
            
            if title_match:
                title = title_match.group(1)
                filename = self._to_kebab_case(title) + '.md'
            else:
                # Use first line or generic name
                first_line = response.content.split('\n')[0].strip()
                if len(first_line) > 5 and len(first_line) < 60:
                    filename = self._to_kebab_case(first_line) + '.md'
                else:
                    filename = f'response-{i+1}.md'
            
            filepath = docs_dir / filename
            
            # Avoid overwriting
            counter = 1
            while filepath.exists():
                stem = filepath.stem
                filepath = docs_dir / f"{stem}-{counter}.md"
                counter += 1
            
            filepath.write_text(response.content, encoding='utf-8')
            print(f"Exported doc: {filepath}")
    
    def _get_extension(self, language: str) -> str:
        """Get file extension for a language."""
        ext_map = {
            'python': 'py',
            'javascript': 'js',
            'typescript': 'ts',
            'bash': 'sh',
            'shell': 'sh',
            'yaml': 'yml',
            'json': 'json',
            'sql': 'sql',
            'html': 'html',
            'css': 'css',
            'markdown': 'md',
            'rust': 'rs',
            'go': 'go',
            'java': 'java',
            'cpp': 'cpp',
            'c': 'c',
        }
        return ext_map.get(language.lower(), 'txt')


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Parse Claude conversation exports and organize content'
    )
    parser.add_argument(
        'input_file',
        type=str,
        help='Input markdown file from Claude export'
    )
    parser.add_argument(
        '-o', '--output-dir',
        type=str,
        default='.',
        help='Output directory (default: current directory)'
    )
    parser.add_argument(
        '--artifacts-only',
        action='store_true',
        help='Only export artifacts (skip scripts and docs)'
    )
    parser.add_argument(
        '--scripts-only',
        action='store_true',
        help='Only export scripts (skip artifacts and docs)'
    )
    parser.add_argument(
        '--docs-only',
        action='store_true',
        help='Only export docs (skip artifacts and scripts)'
    )
    
    args = parser.parse_args()
    
    # Parse the conversation
    parser_obj = ConversationParser(args.input_file)
    parser_obj.parse()
    
    output_dir = Path(args.output_dir)
    
    print(f"\nParsing: {args.input_file}")
    print(f"Found {len(parser_obj.artifacts)} artifacts")
    print(f"Found {len(parser_obj.code_blocks)} code blocks")
    print(f"Found {len(parser_obj.responses)} responses\n")
    
    # Export based on flags
    if not (args.scripts_only or args.docs_only):
        parser_obj.export_artifacts(output_dir)
    
    if not (args.artifacts_only or args.docs_only):
        parser_obj.export_scripts(output_dir / 'scripts')
    
    if not (args.artifacts_only or args.scripts_only):
        parser_obj.export_docs(output_dir / 'docs')
    
    print("\n✓ Export complete!")


if __name__ == '__main__':
    main()
