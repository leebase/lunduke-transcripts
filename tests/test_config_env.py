import os

from lunduke_transcripts.config import load_config, load_env_file


def test_env_file_and_overrides(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "LLM_PROVIDER=openrouter",
                "LLM_MODEL=openai/gpt-4.1-mini",
                "OPENROUTER_API_KEY=test-key",
                "ENABLE_ARTICLE=true",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    config_file = tmp_path / "channels.toml"
    config_file.write_text(
        """
[app]
data_dir = "data"
enable_cleanup = false
enable_article = false

[llm]
provider = "openai"
model = "gpt-4.1-mini"

[[channels]]
name = "Example"
url = "https://www.youtube.com/@example/videos"
""".strip() + "\n",
        encoding="utf-8",
    )

    for key in ["LLM_PROVIDER", "LLM_MODEL", "OPENROUTER_API_KEY", "ENABLE_ARTICLE"]:
        monkeypatch.delenv(key, raising=False)
        os.environ.pop(key, None)

    load_env_file(env_file)
    config = load_config(config_file)
    assert config.llm.provider == "openrouter"
    assert config.llm.model == "openai/gpt-4.1-mini"
    assert config.app.enable_article is True
