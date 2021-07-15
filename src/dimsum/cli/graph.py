import os
import logging
import asyncclick as click
import jinja2

from model import *
import scopes

import cli.utils as utils

log = logging.getLogger("dimsum.cli")


@click.group()
def commands():
    pass


def get_color(e: Entity) -> str:
    map = {
        RootEntityClass: "white",
        scopes.LivingClass: "darkseagreen",
        scopes.ItemClass: "khaki",
        scopes.ExitClass: "salmon",
        scopes.AreaClass: "skyblue",
    }
    return map[e.klass]


@commands.command()
@click.option(
    "--path", required=True, help="Database to graph.", type=click.Path(exists=True)
)
@click.option("--output", required=True, help="File to generate.", type=click.Path())
async def graph(path: str, output: str):
    """Graph the entities in a database."""
    name = os.path.splitext(path)[0]
    template_loader = jinja2.FileSystemLoader(searchpath="./templates")
    template_env = jinja2.Environment(loader=template_loader)
    template = template_env.get_template("graph.template")

    domain = await utils.open_domain(path)
    with domain.session() as session:
        with open(output, "w") as file:
            file.write(
                template.render(
                    registrar=session.registrar,
                    world=session.world,
                    get_color=get_color,
                )
            )
            file.write("\n\n")
