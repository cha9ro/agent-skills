#!/usr/bin/env python3
"""
Skill Installer

Reads a skills.yaml manifest and installs skills from defined sources
to specified destinations.

Usage:
    python scripts/install_skills.py [--manifest skills.yaml] [--dry-run]

Options:
    --manifest PATH    Path to skills.yaml manifest (default: ./skills.yaml)
    --dry-run         Show what would be installed without copying files
    --force           Overwrite existing skills in destination
"""

import argparse
import os
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Any

try:
    import yaml
except ImportError:
    print("Error: PyYAML is required. Install with: pip install pyyaml")
    sys.exit(1)


class SkillInstaller:
    def __init__(self, manifest_path: str, dry_run: bool = False, force: bool = False):
        self.manifest_path = Path(manifest_path)
        self.dry_run = dry_run
        self.force = force
        self.base_dir = self.manifest_path.parent.absolute()

        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {manifest_path}")

        with open(self.manifest_path, 'r') as f:
            self.manifest = yaml.safe_load(f)

        self._validate_manifest()

    def _validate_manifest(self):
        """Validate manifest structure"""
        if 'version' not in self.manifest:
            raise ValueError("Manifest must include 'version' field")

        if self.manifest['version'] != 1:
            raise ValueError(f"Unsupported manifest version: {self.manifest['version']}")

        if 'sources' not in self.manifest:
            raise ValueError("Manifest must include 'sources' section")

        if 'install' not in self.manifest:
            raise ValueError("Manifest must include 'install' section")

        if not isinstance(self.manifest['install'], list):
            raise ValueError("'install' must be a list")

    def _resolve_source_path(self, source_ref: str) -> Path:
        """
        Resolve a source reference to an absolute path.

        Format: <source_name>:<relative_path>
        Example: hub:custom/my-skill
        """
        if ':' not in source_ref:
            raise ValueError(f"Invalid source reference format: {source_ref}. Expected '<source>:<path>'")

        source_name, rel_path = source_ref.split(':', 1)

        if source_name not in self.manifest['sources']:
            raise ValueError(f"Unknown source: {source_name}")

        source = self.manifest['sources'][source_name]

        if source['type'] != 'local':
            raise ValueError(f"Unsupported source type: {source['type']}")

        # Build absolute path: base_dir / root / skills_root / rel_path
        root = Path(source['root'])
        if not root.is_absolute():
            root = self.base_dir / root

        skills_root = source.get('skills_root', '')

        full_path = root / skills_root / rel_path

        if not full_path.exists():
            raise FileNotFoundError(f"Source path not found: {full_path}")

        if not full_path.is_dir():
            raise ValueError(f"Source must be a directory: {full_path}")

        return full_path

    def _resolve_destination_path(self, dest_ref: str) -> Path:
        """Resolve destination path relative to manifest location"""
        dest = Path(dest_ref)
        if not dest.is_absolute():
            dest = self.base_dir / dest
        return dest

    def _copy_skill(self, source: Path, destination: Path, skill_id: str):
        """Copy skill from source to destination"""
        # Check if destination exists
        if destination.exists():
            if not self.force:
                print(f"  ⚠️  Destination exists: {destination}")
                print(f"     Use --force to overwrite")
                return False
            else:
                print(f"  🗑️  Removing existing: {destination}")
                if not self.dry_run:
                    shutil.rmtree(destination)

        # Ensure parent directory exists
        if not self.dry_run:
            destination.parent.mkdir(parents=True, exist_ok=True)

        # Copy the skill
        print(f"  📦 Copying: {source.name}")
        print(f"     From: {source}")
        print(f"     To:   {destination}")

        if not self.dry_run:
            shutil.copytree(source, destination, dirs_exist_ok=False)

        # Verify SKILL.md exists
        skill_md = destination / "SKILL.md"
        if not self.dry_run and not skill_md.exists():
            print(f"  ⚠️  Warning: SKILL.md not found in {destination}")

        return True

    def install(self):
        """Install all skills from manifest"""
        print(f"📚 Skill Installer")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"Manifest: {self.manifest_path}")
        print(f"Base dir: {self.base_dir}")

        if self.dry_run:
            print("🔍 DRY RUN MODE - No files will be copied")

        print(f"\n📋 Installing {len(self.manifest['install'])} skill(s)...\n")

        success_count = 0
        error_count = 0
        skip_count = 0

        for idx, skill_config in enumerate(self.manifest['install'], 1):
            skill_id = skill_config.get('id', f'skill-{idx}')
            source_ref = skill_config.get('from')
            dest_ref = skill_config.get('to')

            print(f"{idx}. {skill_id}")

            try:
                if not source_ref:
                    raise ValueError("Missing 'from' field")
                if not dest_ref:
                    raise ValueError("Missing 'to' field")

                source_path = self._resolve_source_path(source_ref)
                dest_path = self._resolve_destination_path(dest_ref)

                result = self._copy_skill(source_path, dest_path, skill_id)

                if result:
                    success_count += 1
                    print(f"  ✅ Installed successfully\n")
                else:
                    skip_count += 1
                    print(f"  ⏭️  Skipped\n")

            except Exception as e:
                error_count += 1
                print(f"  ❌ Error: {e}\n")

        # Summary
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"📊 Summary:")
        print(f"   ✅ Successful: {success_count}")
        if skip_count > 0:
            print(f"   ⏭️  Skipped:    {skip_count}")
        if error_count > 0:
            print(f"   ❌ Errors:     {error_count}")

        if self.dry_run:
            print(f"\n💡 Run without --dry-run to actually install skills")

        return error_count == 0


def main():
    parser = argparse.ArgumentParser(
        description='Install skills from a YAML manifest',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--manifest',
        default='skills.yaml',
        help='Path to skills.yaml manifest (default: skills.yaml)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be installed without copying files'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Overwrite existing skills in destination'
    )

    args = parser.parse_args()

    try:
        installer = SkillInstaller(
            manifest_path=args.manifest,
            dry_run=args.dry_run,
            force=args.force
        )
        success = installer.install()
        sys.exit(0 if success else 1)

    except Exception as e:
        print(f"❌ Fatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
