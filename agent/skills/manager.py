"""
Skill manager for managing skill lifecycle and operations.
"""

import os
import json
from typing import Dict, List, Optional
from pathlib import Path
from common.log import logger
from agent.skills.types import Skill, SkillEntry, SkillSnapshot
from agent.skills.loader import SkillLoader
from agent.skills.formatter import format_skill_entries_for_prompt

SKILLS_CONFIG_FILE = "skills_config.json"


class SkillManager:
    """Manages skills for an agent."""

    def __init__(
        self,
        builtin_dir: Optional[str] = None,
        custom_dir: Optional[str] = None,
        config: Optional[Dict] = None,
        tenant_id: str = "",
        agent_id: str = "",
    ):
        """
        Initialize the skill manager.

        :param builtin_dir: Built-in skills directory (project root ``skills/``)
        :param custom_dir: Custom skills directory (workspace ``skills/``)
        :param config: Configuration dictionary
        """
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.builtin_dir = builtin_dir or os.path.join(project_root, 'skills')
        self.custom_dir = custom_dir or os.path.join(project_root, 'workspace', 'skills')
        self.config = config or {}
        self._skills_config_path = os.path.join(self.custom_dir, SKILLS_CONFIG_FILE)
        self._platform_scope = self._resolve_platform_scope(tenant_id=tenant_id, agent_id=agent_id)

        # skills_config: full skill metadata keyed by name
        # { "web-fetch": {"name": ..., "description": ..., "source": ..., "enabled": true}, ... }
        self.skills_config: Dict[str, dict] = {}

        self.loader = SkillLoader()
        self.skills: Dict[str, SkillEntry] = {}

        # Load skills on initialization
        self.refresh_skills()

    def refresh_skills(self):
        """Reload all skills from builtin and custom directories, then sync config."""
        self.skills = self.loader.load_all_skills(
            builtin_dir=self.builtin_dir,
            custom_dir=self.custom_dir,
        )
        self._sync_skills_config()
        logger.debug(f"SkillManager: Loaded {len(self.skills)} skills")

    @staticmethod
    def _platform_config_service():
        from cow_platform.services.skill_config_service import SkillConfigService

        return SkillConfigService()

    @staticmethod
    def _resolve_platform_scope(*, tenant_id: str = "", agent_id: str = "") -> tuple[str, str] | None:
        explicit_tenant_id = str(tenant_id or "").strip()
        explicit_agent_id = str(agent_id or "").strip()
        if explicit_tenant_id and explicit_agent_id:
            return explicit_tenant_id, explicit_agent_id
        try:
            from cow_platform.runtime.scope import get_current_runtime_context

            runtime_context = get_current_runtime_context()
            if runtime_context is not None and runtime_context.tenant_id and runtime_context.agent_id:
                return runtime_context.tenant_id, runtime_context.agent_id
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------
    # skills config backend management
    # ------------------------------------------------------------------
    def _load_skills_config(self) -> Dict[str, dict]:
        """Load skill config from the platform DB or legacy skills_config.json."""
        if self._platform_scope is not None:
            try:
                return self._platform_config_service().list_skill_configs(
                    tenant_id=self._platform_scope[0],
                    agent_id=self._platform_scope[1],
                )
            except Exception as e:
                logger.warning(f"[SkillManager] Failed to load platform skill config: {e}")
                return {}
        if not os.path.exists(self._skills_config_path):
            return {}
        try:
            with open(self._skills_config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception as e:
            logger.warning(f"[SkillManager] Failed to load {SKILLS_CONFIG_FILE}: {e}")
        return {}

    def _save_skills_config(self, *, invalidate: bool = False):
        """Persist skill config to the platform DB or legacy skills_config.json."""
        if self._platform_scope is not None:
            try:
                self._platform_config_service().save_skill_configs(
                    tenant_id=self._platform_scope[0],
                    agent_id=self._platform_scope[1],
                    configs=self.skills_config,
                    invalidate=invalidate,
                )
            except Exception as e:
                logger.error(f"[SkillManager] Failed to save platform skill config: {e}")
            return
        os.makedirs(self.custom_dir, exist_ok=True)
        try:
            with open(self._skills_config_path, "w", encoding="utf-8") as f:
                json.dump(self.skills_config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[SkillManager] Failed to save {SKILLS_CONFIG_FILE}: {e}")

    def _sync_skills_config(self):
        """
        Merge directory-scanned skills with the persisted config file.

        - New skills: use metadata.default_enabled as initial enabled state.
        - Existing skills: preserve their persisted enabled state.
        - Skills that no longer exist on disk are removed.
        - name/description/source are always refreshed from the latest scan.
        """
        saved = self._load_skills_config()
        merged: Dict[str, dict] = {}

        for name, entry in self.skills.items():
            skill = entry.skill
            prev = saved.get(name, {})
            category = prev.get("category", "skill")

            if name in saved:
                enabled = prev.get("enabled", True)
            else:
                enabled = entry.metadata.default_enabled if entry.metadata else True

            entry_dict = {
                "name": name,
                "description": skill.description,
                "source": skill.source,
                "enabled": enabled,
                "category": category,
            }
            display_name = prev.get("display_name")
            if display_name:
                entry_dict["display_name"] = display_name
            merged[name] = entry_dict

        self.skills_config = merged
        if merged != saved:
            self._save_skills_config(invalidate=False)

    def is_skill_enabled(self, name: str) -> bool:
        """
        Check if a skill is enabled according to skills_config.

        :param name: skill name
        :return: True if enabled (default True if not in config)
        """
        entry = self.skills_config.get(name)
        if entry is None:
            return True
        return entry.get("enabled", True)

    def set_skill_enabled(self, name: str, enabled: bool):
        """
        Set a skill's enabled state and persist.

        :param name: skill name
        :param enabled: True to enable, False to disable
        """
        if name not in self.skills_config:
            raise ValueError(f"skill '{name}' not found in config")
        self.skills_config[name]["enabled"] = enabled
        self._save_skills_config(invalidate=True)

    def set_runtime_skill_enabled(self, name: str, enabled: bool):
        """Set enabled state for the current Agent runtime without persisting it."""
        if name not in self.skills_config:
            raise ValueError(f"skill '{name}' not found in config")
        self.skills_config[name]["enabled"] = enabled

    def get_skills_config(self) -> Dict[str, dict]:
        """
        Return the full skills_config dict (for query API).

        :return: copy of skills_config
        """
        return dict(self.skills_config)
    
    def get_skill(self, name: str) -> Optional[SkillEntry]:
        """
        Get a skill by name.
        
        :param name: Skill name
        :return: SkillEntry or None if not found
        """
        return self.skills.get(name)
    
    def list_skills(self) -> List[SkillEntry]:
        """
        Get all loaded skills.
        
        :return: List of all skill entries
        """
        return list(self.skills.values())
    
    @staticmethod
    def _normalize_skill_filter(skill_filter: Optional[List[str]]) -> Optional[List[str]]:
        """Normalize a skill_filter list into a flat list of stripped names."""
        if skill_filter is None:
            return None
        normalized = []
        for item in skill_filter:
            if isinstance(item, str):
                name = item.strip()
                if name:
                    normalized.append(name)
            elif isinstance(item, list):
                for subitem in item:
                    if isinstance(subitem, str):
                        name = subitem.strip()
                        if name:
                            normalized.append(name)
        return normalized or None

    def filter_skills(
        self,
        skill_filter: Optional[List[str]] = None,
        include_disabled: bool = False,
    ) -> List[SkillEntry]:
        """
        Filter skills that are eligible (enabled + requirements met).

        :param skill_filter: List of skill names to include (None = all)
        :param include_disabled: Whether to include disabled skills
        :return: Filtered list of eligible skill entries
        """
        from agent.skills.config import should_include_skill

        entries = list(self.skills.values())

        entries = [e for e in entries if should_include_skill(e, self.config)]

        normalized = self._normalize_skill_filter(skill_filter)
        if normalized is not None:
            entries = [e for e in entries if e.skill.name in normalized]

        if not include_disabled:
            entries = [e for e in entries if self.is_skill_enabled(e.skill.name)]

        from config import conf
        if not conf().get("knowledge", True):
            entries = [e for e in entries if e.skill.name != "knowledge-wiki"]

        return entries

    def filter_unavailable_skills(
        self,
        skill_filter: Optional[List[str]] = None,
    ) -> tuple:
        """
        Find skills that are enabled but have unmet requirements.

        :param skill_filter: Optional list of skill names to include
        :return: Tuple of (entries, missing_map) where missing_map maps
                 skill name to its missing requirements dict
        """
        from agent.skills.config import should_include_skill, get_missing_requirements

        entries = list(self.skills.values())

        # Only enabled skills
        entries = [e for e in entries if self.is_skill_enabled(e.skill.name)]

        normalized = self._normalize_skill_filter(skill_filter)
        if normalized is not None:
            entries = [e for e in entries if e.skill.name in normalized]

        # Keep only those that fail should_include_skill (requirements not met)
        unavailable = []
        missing_map: Dict[str, dict] = {}
        for e in entries:
            if not should_include_skill(e, self.config):
                missing = get_missing_requirements(e)
                if missing:
                    unavailable.append(e)
                    missing_map[e.skill.name] = missing

        return unavailable, missing_map

    def build_skills_prompt(
        self,
        skill_filter: Optional[List[str]] = None,
    ) -> str:
        """
        Build a formatted prompt containing available skills
        and brief hints for unavailable ones.

        :param skill_filter: Optional list of skill names to include
        :return: Formatted skills prompt
        """
        from common.log import logger
        from agent.skills.formatter import format_unavailable_skills_for_prompt

        eligible = self.filter_skills(skill_filter=skill_filter, include_disabled=False)
        logger.debug(f"[SkillManager] Eligible: {len(eligible)} skills (total: {len(self.skills)})")
        if eligible:
            skill_names = [e.skill.name for e in eligible]
            logger.debug(f"[SkillManager] Eligible skills: {skill_names}")

        result = format_skill_entries_for_prompt(eligible)

        unavailable, missing_map = self.filter_unavailable_skills(skill_filter=skill_filter)
        if unavailable:
            unavailable_names = [e.skill.name for e in unavailable]
            logger.debug(f"[SkillManager] Unavailable skills (setup needed): {unavailable_names}")
            result += format_unavailable_skills_for_prompt(unavailable, missing_map)

        logger.debug(f"[SkillManager] Generated prompt length: {len(result)}")
        return result
    
    def build_skill_snapshot(
        self,
        skill_filter: Optional[List[str]] = None,
        version: Optional[int] = None,
    ) -> SkillSnapshot:
        """
        Build a snapshot of skills for a specific run.
        
        :param skill_filter: Optional list of skill names to include
        :param version: Optional version number for the snapshot
        :return: SkillSnapshot
        """
        entries = self.filter_skills(skill_filter=skill_filter, include_disabled=False)
        prompt = format_skill_entries_for_prompt(entries)
        
        skills_info = []
        resolved_skills = []
        
        for entry in entries:
            skills_info.append({
                'name': entry.skill.name,
                'primary_env': entry.metadata.primary_env if entry.metadata else None,
            })
            resolved_skills.append(entry.skill)
        
        return SkillSnapshot(
            prompt=prompt,
            skills=skills_info,
            resolved_skills=resolved_skills,
            version=version,
        )
    
    def sync_skills_to_workspace(self, target_workspace_dir: str):
        """
        Sync all loaded skills to a target workspace directory.
        
        This is useful for sandbox environments where skills need to be copied.
        
        :param target_workspace_dir: Target workspace directory
        """
        import shutil
        
        target_skills_dir = os.path.join(target_workspace_dir, 'skills')
        
        # Remove existing skills directory
        if os.path.exists(target_skills_dir):
            shutil.rmtree(target_skills_dir)
        
        # Create new skills directory
        os.makedirs(target_skills_dir, exist_ok=True)
        
        # Copy each skill
        for entry in self.skills.values():
            skill_name = entry.skill.name
            source_dir = entry.skill.base_dir
            target_dir = os.path.join(target_skills_dir, skill_name)
            
            try:
                shutil.copytree(source_dir, target_dir)
                logger.debug(f"Synced skill '{skill_name}' to {target_dir}")
            except Exception as e:
                logger.warning(f"Failed to sync skill '{skill_name}': {e}")
        
        logger.info(f"Synced {len(self.skills)} skills to {target_skills_dir}")
    
    def get_skill_by_key(self, skill_key: str) -> Optional[SkillEntry]:
        """
        Get a skill by its skill key (which may differ from name).
        
        :param skill_key: Skill key to look up
        :return: SkillEntry or None
        """
        for entry in self.skills.values():
            if entry.metadata and entry.metadata.skill_key == skill_key:
                return entry
            if entry.skill.name == skill_key:
                return entry
        return None
