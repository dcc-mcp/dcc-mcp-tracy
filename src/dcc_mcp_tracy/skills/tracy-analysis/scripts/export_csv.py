from dcc_mcp_core.skill import skill_entry, skill_success

from dcc_mcp_tracy.runtime import export_csv


@skill_entry
def main(trace_file: str, output_file: str, **kwargs):
    result = export_csv(trace_file, output_file, **kwargs)
    return skill_success("Tracy zone statistics exported.", **result)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
