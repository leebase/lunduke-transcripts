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
enable_asr_fallback = true
asr_provider = "fast-whisper"
asr_model = "small.en"
frame_capture_enabled = true
frame_capture_threshold = 0.4
frame_image_format = "png"

[llm]
provider = "openai"
model = "gpt-4.1-mini"
router_enabled = true
router_repo_path = "/Users/leeharrington/projects/lee-llm-router"
router_config_path = "config/tutorial-llm-router.yaml"

[llm.router_roles]
"tutorial.writer" = "tutorial_writer"
"tutorial.technical-review" = "tutorial_reviewer"

[[channels]]
name = "Example"
url = "https://www.youtube.com/@example/videos"

[[videos]]
name = "One video"
url = "https://www.youtube.com/watch?v=i6idieq9bso"
clip_start = "00:30:40"
clip_end = "01:12:35"
force_asr = true

[[files]]
name = "One file"
path = "/tmp/demo.mp4"
clip_start = "00:00:05"
clip_end = "00:00:30"
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
    assert config.llm.router_enabled is True
    assert config.llm.router_repo_path == "/Users/leeharrington/projects/lee-llm-router"
    assert config.llm.router_config_path == "config/tutorial-llm-router.yaml"
    assert config.llm.router_roles["tutorial.writer"] == "tutorial_writer"
    assert config.app.enable_article is True
    assert config.app.enable_asr_fallback is True
    assert config.app.asr_provider == "fast-whisper"
    assert config.app.frame_capture_enabled is True
    assert config.app.frame_capture_threshold == 0.4
    assert config.app.frame_image_format == "png"
    assert len(config.channels) == 1
    assert len(config.videos) == 1
    assert len(config.files) == 1
    assert config.videos[0].clip_start == "00:30:40"
    assert config.videos[0].clip_end == "01:12:35"
    assert config.videos[0].force_asr is True
    assert config.files[0].path == "/tmp/demo.mp4"
    assert config.files[0].clip_start == "00:00:05"
    assert config.files[0].clip_end == "00:00:30"
