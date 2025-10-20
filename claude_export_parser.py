#!/usr/bin/env python3
"""
Claude Conversation Export Parser - Artifacts Only Version
Extracts artifacts from Claude conversation exports and writes them to their specified paths.
"""

import re
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class Artifact:
    """Represents an artifact with path and content."""
    path: Optional[str]
    title: str
    content: str


class ConversationParser:
    """Parser for Claude conversation exports."""
    
    # Pattern to match artifact headers like: ### path/to/file.ext
    ARTIFACT_PATTERN = re.compile(
        r'^###\s+([^\s]+(?:/[^\s]+)*\.[a-zA-Z0-9]+)\s*$\s*```[\w]*\s*\n(.*?)\n```',
        re.MULTILINE | re.DOTALL
    )
    
    def __init__(self, filepath: str):
        self.filepath = Path(filepath)
        self.content = self.filepath.read_text(encoding='utf-8')
        self.artifacts: list[Artifact] = []
    
    def parse(self) -> None:
        """Parse the conversation and extract artifacts."""
        self._extract_artifacts()
    
    def _extract_artifacts(self) -> None:
        """Extract artifacts from the content."""
        for match in self.ARTIFACT_PATTERN.finditer(self.content):
            path = match.group(1).strip()
            content = match.group(2).strip()
            
            # Use the path as both the path and title
            self.artifacts.append(Artifact(
                path=path,
                title=Path(path).name,
                content=content
            ))
    
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
            print(f"Created: {filepath}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Extract artifacts from Claude conversation exports'
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
    
    args = parser.parse_args()
    
    # Parse the conversation
    parser_obj = ConversationParser(args.input_file)
    parser_obj.parse()
    
    output_dir = Path(args.output_dir)
    
    print(f"\nParsing: {args.input_file}")
    print(f"Found {len(parser_obj.artifacts)} artifacts\n")
    
    # Export artifacts
    parser_obj.export_artifacts(output_dir)
    
    print("\n✓ Export complete!")


if __name__ == '__main__':
    main()