from adobe.dcc_mcp import action_result
from dcc_mcp_core.skill import skill_entry

from dcc_mcp_illustrator.operations import create_rectangle


@skill_entry
def main(**kwargs):
    return action_result("Illustrator rectangle created.", lambda: create_rectangle(**kwargs))


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
