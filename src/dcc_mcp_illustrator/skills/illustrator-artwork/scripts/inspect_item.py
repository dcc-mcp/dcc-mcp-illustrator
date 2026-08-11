from adobe.dcc_mcp import action_result
from dcc_mcp_core.skill import skill_entry

from dcc_mcp_illustrator.operations import inspect_item


@skill_entry
def main(**kwargs):
    return action_result("Illustrator item inspected.", inspect_item, **kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
