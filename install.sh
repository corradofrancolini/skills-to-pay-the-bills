#!/usr/bin/env bash
set -euo pipefail

# Skills to Pay the Bills -- Interactive Installer
# Copies selected skills/commands into your Claude Code project.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="$SCRIPT_DIR/skills"
COMMANDS_DIR="$SCRIPT_DIR/commands"

# Colors (disabled if not a terminal)
if [[ -t 1 ]]; then
  BOLD="\033[1m"
  DIM="\033[2m"
  GREEN="\033[32m"
  YELLOW="\033[33m"
  CYAN="\033[36m"
  RESET="\033[0m"
else
  BOLD="" DIM="" GREEN="" YELLOW="" CYAN="" RESET=""
fi

usage() {
  echo "Usage: $0 <target-project-path>"
  echo ""
  echo "Installs selected Claude Code skills into your project."
  echo ""
  echo "Examples:"
  echo "  $0 /path/to/my-project"
  echo "  $0 ."
  exit 1
}

# -- Validate args --

if [[ $# -lt 1 ]]; then
  usage
fi

TARGET="$(cd "$1" 2>/dev/null && pwd)" || {
  echo "Error: '$1' is not a valid directory"
  exit 1
}

echo -e "${BOLD}Skills to Pay the Bills${RESET}"
echo -e "${DIM}Installing to: $TARGET${RESET}"
echo ""

# -- List available skills --

AVAILABLE_SKILLS=()
SKILL_DESCS=()

for skill_dir in "$SKILLS_DIR"/*/; do
  skill_name="$(basename "$skill_dir")"
  skill_file="$skill_dir/SKILL.md"
  if [[ -f "$skill_file" ]]; then
    # Extract description from frontmatter
    desc=$(sed -n 's/^description: *//p' "$skill_file" | head -1)
    AVAILABLE_SKILLS+=("$skill_name")
    SKILL_DESCS+=("$desc")
  fi
done

echo -e "${BOLD}Available skills:${RESET}"
echo ""
for i in "${!AVAILABLE_SKILLS[@]}"; do
  printf "  ${CYAN}%d${RESET}) %-20s %s\n" "$((i + 1))" "${AVAILABLE_SKILLS[$i]}" "${DIM}${SKILL_DESCS[$i]}${RESET}"
done
echo ""

# -- Skill selection --

echo -e "Enter skill numbers to install (comma-separated), or ${CYAN}a${RESET} for all:"
read -r selection

SELECTED_SKILLS=()
if [[ "$selection" == "a" || "$selection" == "A" || "$selection" == "all" ]]; then
  SELECTED_SKILLS=("${AVAILABLE_SKILLS[@]}")
else
  IFS=',' read -ra nums <<< "$selection"
  for num in "${nums[@]}"; do
    num=$(echo "$num" | tr -d ' ')
    if [[ "$num" =~ ^[0-9]+$ ]] && (( num >= 1 && num <= ${#AVAILABLE_SKILLS[@]} )); then
      SELECTED_SKILLS+=("${AVAILABLE_SKILLS[$((num - 1))]}")
    else
      echo "Skipping invalid selection: $num"
    fi
  done
fi

if [[ ${#SELECTED_SKILLS[@]} -eq 0 ]]; then
  echo "No skills selected."
  exit 0
fi

# -- project-index: skill has a command variant too --

INSTALL_PI_COMMAND=false
for skill in "${SELECTED_SKILLS[@]}"; do
  if [[ "$skill" == "project-index" ]]; then
    echo ""
    echo -e "project-index can also be installed as a ${BOLD}global command${RESET} (~/.claude/commands/)."
    echo -e "  1) Skill only (project-level)"
    echo -e "  2) Command only (global)"
    echo -e "  3) Both"
    read -rp "Choice [1]: " pi_choice
    pi_choice="${pi_choice:-1}"
    case "$pi_choice" in
      2)
        SELECTED_SKILLS=("${SELECTED_SKILLS[@]/project-index/}")
        INSTALL_PI_COMMAND=true
        ;;
      3)
        INSTALL_PI_COMMAND=true
        ;;
    esac
    break
  fi
done

# -- Global commands --

AVAILABLE_COMMANDS=()
COMMAND_DESCS=()

for cmd_file in "$COMMANDS_DIR"/*.md; do
  cmd_name="$(basename "$cmd_file" .md)"
  # project-index handled separately above
  [[ "$cmd_name" == "project-index" ]] && continue
  first_line=$(head -1 "$cmd_file")
  AVAILABLE_COMMANDS+=("$cmd_name")
  COMMAND_DESCS+=("$first_line")
done

SELECTED_COMMANDS=()
if [[ ${#AVAILABLE_COMMANDS[@]} -gt 0 ]]; then
  echo ""
  echo -e "${BOLD}Available global commands:${RESET}"
  echo ""
  for i in "${!AVAILABLE_COMMANDS[@]}"; do
    printf "  ${CYAN}%d${RESET}) %-20s %s\n" "$((i + 1))" "${AVAILABLE_COMMANDS[$i]}" "${DIM}${COMMAND_DESCS[$i]}${RESET}"
  done
  echo ""
  echo -e "Enter command numbers to install (comma-separated), ${CYAN}a${RESET} for all, or ${DIM}enter${RESET} to skip:"
  read -r cmd_selection
  if [[ "$cmd_selection" == "a" || "$cmd_selection" == "A" || "$cmd_selection" == "all" ]]; then
    SELECTED_COMMANDS=("${AVAILABLE_COMMANDS[@]}")
  elif [[ -n "$cmd_selection" ]]; then
    IFS=',' read -ra nums <<< "$cmd_selection"
    for num in "${nums[@]}"; do
      num=$(echo "$num" | tr -d ' ')
      if [[ "$num" =~ ^[0-9]+$ ]] && (( num >= 1 && num <= ${#AVAILABLE_COMMANDS[@]} )); then
        SELECTED_COMMANDS+=("${AVAILABLE_COMMANDS[$((num - 1))]}")
      else
        echo "Skipping invalid selection: $num"
      fi
    done
  fi
fi

# -- Install skills --

echo ""
INSTALLED=()
ALL_PLACEHOLDERS=()

for skill in "${SELECTED_SKILLS[@]}"; do
  [[ -z "$skill" ]] && continue
  src="$SKILLS_DIR/$skill"
  dest="$TARGET/.claude/skills/$skill"
  mkdir -p "$dest"
  cp "$src/SKILL.md" "$dest/SKILL.md"
  INSTALLED+=("$skill")

  # Collect placeholders
  placeholders=$(grep -oE '\{\{[A-Z_]+\}\}' "$dest/SKILL.md" 2>/dev/null | sort -u || true)
  if [[ -n "$placeholders" ]]; then
    while IFS= read -r ph; do
      ALL_PLACEHOLDERS+=("$skill: $ph")
    done <<< "$placeholders"
  fi
done

# -- Install commands --

cmd_dest="$HOME/.claude/commands"

if [[ "$INSTALL_PI_COMMAND" == true ]]; then
  mkdir -p "$cmd_dest"
  cp "$COMMANDS_DIR/project-index.md" "$cmd_dest/project-index.md"
  INSTALLED+=("command:project-index")
fi

for cmd in "${SELECTED_COMMANDS[@]}"; do
  [[ -z "$cmd" ]] && continue
  mkdir -p "$cmd_dest"
  cp "$COMMANDS_DIR/$cmd.md" "$cmd_dest/$cmd.md"
  INSTALLED+=("command:$cmd")
done

# -- Report --

echo -e "${GREEN}Installed ${#INSTALLED[@]} item(s):${RESET}"
for item in "${INSTALLED[@]}"; do
  echo "  - $item"
done

if [[ ${#ALL_PLACEHOLDERS[@]} -gt 0 ]]; then
  echo ""
  echo -e "${YELLOW}Placeholders to fill in:${RESET}"
  # Deduplicate and print
  printf '%s\n' "${ALL_PLACEHOLDERS[@]}" | sort -u | while IFS= read -r line; do
    echo "  $line"
  done
  echo ""
  echo -e "Open each SKILL.md and replace the ${CYAN}{{PLACEHOLDER}}${RESET} values with your project's specifics."
  echo -e "See ${DIM}docs/CUSTOMIZATION.md${RESET} for details."
fi

echo ""
echo "Done."
