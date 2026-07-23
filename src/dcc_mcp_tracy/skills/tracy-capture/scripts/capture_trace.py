from dcc_mcp_core.skill import skill_entry, skill_success

from dcc_mcp_tracy.runtime import capture_trace


@skill_entry
def main(output_file: str, **kwargs):
    result = capture_trace(output_file, **kwargs)
    return skill_success("Tracy trace captured.", **result)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
