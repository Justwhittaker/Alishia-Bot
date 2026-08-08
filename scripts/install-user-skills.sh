#!/usr/bin/env bash
# Install Alishia Bot / Justin Whittaker skills into the Cursor USER profile
# so they appear under Customize → Skills → User (not only Workspace).
#
# Targets (per Cursor docs):
#   ~/.cursor/skills/<name>/SKILL.md
#   ~/.agents/skills/<name>/SKILL.md
#
# Usage (from repo root, on Justin's Desktop or any machine):
#   bash scripts/install-user-skills.sh
#   bash scripts/install-user-skills.sh --dry-run

set -euo pipefail

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${REPO_ROOT}/.cursor/skills"
USER_SKILLS="${HOME}/.cursor/skills"
AGENTS_SKILLS="${HOME}/.agents/skills"

if [[ ! -d "${SRC}" ]]; then
  echo "No project skills at ${SRC}" >&2
  exit 1
fi

echo "Justin Whittaker user profile skill install"
echo "  source : ${SRC}"
echo "  user   : ${USER_SKILLS}"
echo "  agents : ${AGENTS_SKILLS}"
echo "  home   : ${HOME}"
echo

installed=0
for skill_dir in "${SRC}"/*/; do
  [[ -f "${skill_dir}/SKILL.md" ]] || continue
  name="$(basename "${skill_dir}")"

  if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "DRY-RUN would install: ${name}"
    installed=$((installed + 1))
    continue
  fi

  mkdir -p "${USER_SKILLS}" "${AGENTS_SKILLS}"
  rm -rf "${USER_SKILLS}/${name}" "${AGENTS_SKILLS}/${name}"
  cp -a "${skill_dir}" "${USER_SKILLS}/${name}"
  cp -a "${skill_dir}" "${AGENTS_SKILLS}/${name}"
  # Drop local bytecode if copied
  rm -rf "${USER_SKILLS}/${name}/scripts/__pycache__" \
         "${AGENTS_SKILLS}/${name}/scripts/__pycache__" 2>/dev/null || true
  echo "Installed user skill: ${name}"
  installed=$((installed + 1))
done

echo
echo "Done. ${installed} skill(s) → Customize → Skills → User"
echo "Open Customize in the sidebar, pick Skills, filter scope: User."
if [[ "$(uname -s)" == "Darwin" ]]; then
  echo "Tip: restart Cursor or reload the window if they do not appear yet."
fi
