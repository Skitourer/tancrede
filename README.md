# Tancrède

A desktop assistant for notes, projects and cognitive load.

> **Status: early design.** No usable release yet. The specification lives in [`docs/SPEC.md`](docs/SPEC.md).

## What it aims to be

- **Conversation first**: ask questions about your notes, documents and projects.
- **Sourced answers**: every claim points to a source the app actually retrieved; no invented citations.
- **Your notes are never rewritten**: versioned notes, project memory, visible contradictions.
- **Nothing happens without you**: actions are proposals you confirm.
- **Bring your own model**: any OpenAI-compatible endpoint (Ollama, llama.cpp, LM Studio, vLLM, cloud APIs) or a plugin.

## Two modes

- **`enclave`**: for sensitive environments. Only allowed endpoints can be reached, classification filtering is mandatory, no telemetry, no outbound network beyond your model.
- **`open`**: no restriction; you are clearly warned that data may leave your machine.

## Try it (wave W0: model connection only)

```
uv sync
uv run tancrede check-gateway                    # dev profile, mock model
```

To test your own model, copy [`docs/config.example.toml`](docs/config.example.toml) to
`%LOCALAPPDATA%\Tancrede\config.toml`, start your model server (e.g. Ollama), then from a plain
terminal (not VS Code):

```
uv run tancrede --profile real check-gateway
```

## Development

```
uv sync
uv run pre-commit install
uv run pytest
```

The `dev` profile only reads `fixtures/synthetic/` and only uses mock models. The `real` profile
refuses to start from a VS Code or Claude Code terminal.

## License

[MIT](LICENSE)
