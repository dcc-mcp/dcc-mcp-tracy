from dcc_mcp_core.skill import skill_entry, skill_success

from dcc_mcp_tracy.runtime import get_version


@skill_entry
def main(**_kwargs):
    result = get_version()
    return skill_success("Tracy capture utility resolved.", **result)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
