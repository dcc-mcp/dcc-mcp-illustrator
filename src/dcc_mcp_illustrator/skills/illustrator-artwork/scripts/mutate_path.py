from adobe.dcc_mcp import action_result
from dcc_mcp_core.skill import skill_entry

from dcc_mcp_illustrator.operations import mutate_path


@skill_entry
def main(**kwargs):
    return action_result("Illustrator path updated.", lambda: mutate_path(**kwargs))


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
