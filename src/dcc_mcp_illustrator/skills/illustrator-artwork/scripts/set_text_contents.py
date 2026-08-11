from adobe.dcc_mcp import action_result
from dcc_mcp_core.skill import skill_entry

from dcc_mcp_illustrator.operations import set_text_contents


@skill_entry
def main(**kwargs):
    return action_result("Illustrator text updated.", set_text_contents, **kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
