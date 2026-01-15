# Agent Skills

My personal repository for various skills and tools for AI agents, mainly for coding.

## Features

- **Custom Skills**: Hand-crafted skills for specific development workflows
- **Public Skills**: Curated skills from Anthropic and OpenAI (as submodules)
- **Skill Importer**: Declarative YAML-based skill installation system

## Quick Start

### Using the Skill Importer

This repository includes a skill importer mechanism that allows you to:
1. Pin skill hubs as Git submodules
2. Select skills via YAML manifest
3. Install skills with a single command

See [SKILL_IMPORTER.md](SKILL_IMPORTER.md) for detailed documentation.

**Example:**

```bash
# Install skills from manifest
python scripts/install_skills.py

# Dry run to preview
python scripts/install_skills.py --dry-run
```

### Using This Repository in Your Project

Add this repository as a submodule to your project:

```bash
git submodule add https://github.com/cha9ro/agent-skills.git .skills-hub
git submodule update --init --recursive
```

Create a `skills.yaml` manifest:

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

Copy and run the installer:

```bash
cp .skills-hub/scripts/install_skills.py ./scripts/
python scripts/install_skills.py
```

## Repository Structure

```
agent-skills/
├── skills/
│   ├── custom/           # Custom skills
│   │   ├── unit-test-generator/
│   │   ├── python-project-scaffold/
│   │   └── web-uiux-design/
│   └── public/           # Public skills (submodules)
│       ├── anthropic/    # Anthropic skills
│       └── openai/       # OpenAI skills
├── scripts/
│   └── install_skills.py # Skill installer
├── template/             # Skill template
├── skills.yaml           # Example manifest
└── SKILL_IMPORTER.md     # Importer documentation
```

## Available Skills

### Custom Skills

- **unit-test-generator**: Generate high-quality unit tests using Meta's TestGen-LLM methodology
- **python-project-scaffold**: Scaffold Python projects with best practices
- **web-uiux-design**: UI/UX design guidance and principles

### Public Skills (via submodules)

- **Anthropic**: skill-creator, mcp-builder, web-artifacts-builder, and more
- **OpenAI**: Various skills from OpenAI's skill repository
