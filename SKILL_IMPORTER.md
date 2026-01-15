# Skill Importer

A mechanism for importing and managing skills from various sources using a YAML manifest and Git submodules.

## Overview

The skill importer allows you to:
- **Pin dependencies** using Git submodules for reproducibility
- **Select skills** via a declarative YAML manifest
- **Install skills** to your project with a simple Python script
- **Version control** your skill dependencies at the commit level

## Architecture

### Option A: Hub as Submodule (Recommended)

Pin a skills hub as a Git submodule in your project. Git guarantees dependency pinning, and the manifest focuses on "what to install and where."

**Benefits:**
- High reproducibility in CI and local environments
- Git handles version pinning at the commit SHA level
- Clear separation between hub updates and skill selection

**Project Structure:**

```
my-project/
├── .skills-hub/          # Submodule (pinned to specific commit)
├── skills.yaml           # Selection manifest
└── .agent/skills/        # Installation destination
```

### Adding the Skills Hub

Add this repository (or any skills repository) as a submodule:

```bash
# Add as submodule
git submodule add https://github.com/cha9ro/agent-skills.git .skills-hub

# Initialize and update
git submodule update --init --recursive

# The submodule is now pinned to a specific commit
git add .skills-hub
git commit -m "Add skills hub as submodule"
```

### Updating the Hub

Update the hub only when you want newer skill versions:

```bash
cd .skills-hub
git fetch
git checkout <commit-sha-or-tag>
cd ..
git add .skills-hub
git commit -m "Update skills hub to version X"
```

## Manifest Format

### `skills.yaml`

The manifest defines skill sources and which skills to install.

```yaml
version: 1

# Source definitions
sources:
  # Hub repository (as submodule)
  hub:
    type: local
    root: .skills-hub          # Path to submodule
    skills_root: skills        # Skills directory within hub

  # You can define multiple sources
  # another-hub:
  #   type: local
  #   root: .another-hub
  #   skills_root: skills

# Skills to install
install:
  # Install from hub
  - id: skill-creator
    from: hub:public/anthropic/skills/skill-creator
    to: .agent/skills/skill-creator

  # Install custom skills
  - id: unit-test-generator
    from: hub:custom/unit-test-generator
    to: .agent/skills/unit-test-generator

  # Skills from vendor (if included in hub)
  - id: vercel-ai-routes
    from: hub:vendor/vercel/ai/skills/routes
    to: .agent/skills/vercel-ai-routes
```

### Manifest Fields

#### `version`
- Manifest format version (currently `1`)

#### `sources`
- Named skill sources with configuration
- **type**: Source type (`local` supported)
- **root**: Path to source root (relative to manifest)
- **skills_root**: Skills directory within root

#### `install`
- List of skills to install
- **id**: Skill identifier (for logging)
- **from**: Source reference (`<source>:<relative_path>`)
- **to**: Destination path (relative to manifest)

### Source Resolution

The installer resolves paths as:
```
{base_dir} / {root} / {skills_root} / {relative_path}
```

Example:
```yaml
sources:
  hub:
    type: local
    root: .skills-hub
    skills_root: skills

install:
  - from: hub:custom/my-skill
```

Resolves to: `./.skills-hub/skills/custom/my-skill`

## Installation

### Prerequisites

```bash
pip install pyyaml
```

### Usage

```bash
# Install all skills from manifest
python scripts/install_skills.py

# Dry run (see what would be installed)
python scripts/install_skills.py --dry-run

# Force overwrite existing skills
python scripts/install_skills.py --force

# Use custom manifest path
python scripts/install_skills.py --manifest ./custom/skills.yaml
```

### Command Options

- `--manifest PATH`: Path to skills.yaml (default: `./skills.yaml`)
- `--dry-run`: Show what would be installed without copying files
- `--force`: Overwrite existing skills in destination

## Example Workflow

### 1. Add Skills Hub to Your Project

```bash
# In your project root
git submodule add https://github.com/cha9ro/agent-skills.git .skills-hub
git submodule update --init --recursive
```

### 2. Create `skills.yaml`

```yaml
version: 1

sources:
  hub:
    type: local
    root: .skills-hub
    skills_root: skills

install:
  - id: skill-creator
    from: hub:public/anthropic/skills/skill-creator
    to: .agent/skills/skill-creator
```

### 3. Install Skills

```bash
# Copy install script from hub
cp .skills-hub/scripts/install_skills.py ./scripts/

# Install skills
python scripts/install_skills.py
```

### 4. Update Skills When Needed

```bash
# Update hub to newer version
cd .skills-hub
git fetch
git checkout main  # or specific tag/commit
cd ..

# Reinstall skills with --force
python scripts/install_skills.py --force

# Commit the hub update
git add .skills-hub
git commit -m "Update skills to latest version"
```

## CI/CD Integration

Add skill installation to your CI pipeline:

```yaml
# .github/workflows/ci.yml
steps:
  - name: Checkout code
    uses: actions/checkout@v3
    with:
      submodules: recursive  # Initialize submodules

  - name: Install skills
    run: |
      pip install pyyaml
      python scripts/install_skills.py
```

## Use Case: This Repository

This repository demonstrates the importer by using itself as a source:

```yaml
sources:
  local:
    type: local
    root: .
    skills_root: skills

install:
  - id: skill-creator
    from: local:public/anthropic/skills/skill-creator
    to: .agent/skills/skill-creator
```

This imports the `skill-creator` skill from the Anthropic public skills (available as a submodule).

## Benefits

### Reproducibility
- Git submodules pin exact commit SHAs
- Same skills across all environments (local, CI, production)
- No surprise updates

### Flexibility
- Choose only the skills you need
- Mix skills from multiple sources
- Custom installation paths

### Maintainability
- Update hub independently of skill selection
- Clear audit trail of skill versions
- Easy to add/remove skills

### Simplicity
- YAML manifest is human-readable and version-controllable
- Single command to install all skills
- Dry-run mode for safe testing

## Advanced Usage

### Multiple Sources

```yaml
sources:
  hub:
    type: local
    root: .skills-hub
    skills_root: skills

  company-skills:
    type: local
    root: .company-skills
    skills_root: our-skills

install:
  - id: skill-creator
    from: hub:public/anthropic/skills/skill-creator
    to: .agent/skills/skill-creator

  - id: internal-api-skill
    from: company-skills:api/customer-service
    to: .agent/skills/customer-service-api
```

### Conditional Installation

Use multiple manifest files for different environments:

```bash
# Development
python scripts/install_skills.py --manifest skills.dev.yaml

# Production
python scripts/install_skills.py --manifest skills.prod.yaml
```

## Troubleshooting

### Submodule not initialized

```bash
git submodule update --init --recursive
```

### Skill already exists

Use `--force` to overwrite:

```bash
python scripts/install_skills.py --force
```

### Path resolution errors

Run in dry-run mode to debug:

```bash
python scripts/install_skills.py --dry-run
```

Check that:
- `root` path exists relative to manifest
- `skills_root` path exists within `root`
- `from` path exists within `skills_root`

## Future Enhancements

Potential future features:
- Remote sources (HTTP/Git URLs)
- Skill dependency resolution
- Version constraints and compatibility checks
- Skill verification and validation
- Incremental updates (only changed skills)
