Generates an organized visual map of the current project.

## Instructions

1. **Look for `.project-index.yaml`** in the project root.

2. **If `.project-index.yaml` exists**, read it and use it as a guide:
   - The YAML defines the structure to show: folders, key files, descriptions, tags, groupings
   - Respect the order and groupings defined in the YAML
   - Only show what the YAML lists (do not scan the entire filesystem)

3. **If `.project-index.yaml` does NOT exist**, scan the project:
   - Use `ls` and `find` (max depth 3) to map the structure
   - Group by type: source code, config, docs, tests, build output
   - Show sizes and last modified dates for main folders
   - Ignore: node_modules, .git, __pycache__, .venv, dist, build, .next

4. **Output format** (for both cases):
   - Text tree with indentation (use box-drawing characters: `├──`, `└──`, `│`)
   - For each element: name, size (if relevant), description (if available)
   - Tags in square brackets if defined: [ACTIVE], [MAIN], [LEGACY], [DEPRECATED]
   - Stats section at the top: file counts by type, total size
   - Legend section if tags are used

5. **Answer follow-up questions** about the project based on the generated map.

## `.project-index.yaml` Format

```yaml
project: Project Name
updated: 2026-01-01

stats:
  - "12 prompts"
  - "23 scripts"

legend:
  active: "In use"
  main: "Primary"
  legacy: "Old"

tree:
  - name: "src/"
    desc: "Source code"
    tag: active
    children:
      - name: "index.ts"
        desc: "Entry point"
        tag: main
      - name: "utils/"
        desc: "Shared utilities"

  - name: "docs/"
    desc: "Documentation"
    children:
      - name: "API.md"
        desc: "API reference"
```

## Notes
- Do NOT use emojis in the output
- Use plain text with box-drawing characters for the tree
- If the project is very large, show only the first 2 levels and ask whether to go deeper
