from types import SimpleNamespace

from agent.skills.manager import SkillManager


def _skill_entry(name: str):
    return SimpleNamespace(
        skill=SimpleNamespace(
            name=name,
            description=f"{name} description",
            source="builtin",
        ),
        metadata=SimpleNamespace(default_enabled=True),
    )


def test_platform_skill_manager_uses_db_store_without_writing_json(monkeypatch, tmp_path):
    saved_calls = []

    class FakeSkillConfigService:
        def list_skill_configs(self, *, tenant_id, agent_id):
            assert (tenant_id, agent_id) == ("tenant-a", "agent-a")
            return {
                "skill-a": {
                    "enabled": False,
                    "category": "ops",
                    "display_name": "Skill A",
                }
            }

        def save_skill_configs(self, *, tenant_id, agent_id, configs, invalidate=False):
            saved_calls.append((tenant_id, agent_id, dict(configs), invalidate))
            return dict(configs)

    monkeypatch.setattr(
        "agent.skills.loader.SkillLoader.load_all_skills",
        lambda self, builtin_dir, custom_dir: {"skill-a": _skill_entry("skill-a")},
    )
    monkeypatch.setattr(
        SkillManager,
        "_platform_config_service",
        staticmethod(lambda: FakeSkillConfigService()),
    )

    manager = SkillManager(custom_dir=str(tmp_path / "skills"), tenant_id="tenant-a", agent_id="agent-a")

    assert manager.skills_config["skill-a"]["enabled"] is False
    assert manager.skills_config["skill-a"]["category"] == "ops"
    assert manager.skills_config["skill-a"]["display_name"] == "Skill A"
    assert not (tmp_path / "skills" / "skills_config.json").exists()
    assert saved_calls[-1][3] is False

    manager.set_runtime_skill_enabled("skill-a", True)
    assert saved_calls[-1][3] is False

    manager.set_skill_enabled("skill-a", True)
    assert saved_calls[-1][3] is True
