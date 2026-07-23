from dcc_mcp_core.skill import skill_entry, skill_success

from dcc_mcp_tracy.runtime import summarize_csv


@skill_entry
def main(csv_file: str, limit: int = 20, **_kwargs):
    result = summarize_csv(csv_file, limit)
    return skill_success("Tracy zone statistics summarized.", **result)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
