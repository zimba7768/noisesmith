"""The NoiseSmith MCP server: the tools Claude can call to make sounds."""

from mcp.server.mcpserver import MCPServer

from noisesmith import audio

mcp = MCPServer("noisesmith")


@mcp.tool()
def make_beep(
    name: str = "beep",
    frequency_hz: float = 880.0,
    duration_s: float = 0.3,
    output_dir: str | None = None,
) -> str:
    """Create a simple beep and save it as a WAV file. (Phase 0 test tool.)

    Returns the full path of the saved file.
    """
    if not 20 <= frequency_hz <= 20000:
        raise ValueError("frequency_hz must be between 20 and 20000")
    if not 0.01 <= duration_s <= 10:
        raise ValueError("duration_s must be between 0.01 and 10 seconds")

    folder = audio.resolve_output_dir(output_dir)
    path = folder / f"{audio.safe_name(name)}.wav"
    audio.write_wav(path, audio.beep(frequency_hz, duration_s))
    return str(path)


def main() -> None:
    """Start the server (Claude launches this and talks to it over stdin/stdout)."""
    mcp.run()


if __name__ == "__main__":
    main()
