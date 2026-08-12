from adobe.dcc_mcp import action_result
from dcc_mcp_core.skill import skill_entry

from dcc_mcp_illustrator.operations import list_layers


@skill_entry
def main(**kwargs):
    return action_result("Illustrator layers listed.", lambda: list_layers(**kwargs))


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
