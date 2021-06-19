import logging
import asyncclick as click
import os
import jinja2

import model.world as world
import model.entity as entity
import model.scopes as scopes

import cli.utils as utils

log = logging.getLogger("dimsum-cli")


@click.group()
def commands():
    pass


def get_color(e: entity.Entity) -> str:
    map = {
        entity.RootEntityClass: "white",
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
async def graph(path: str):
    """Graph the entities in a database."""
    world, db = await utils.open_world(path)
    name = os.path.splitext(path)[0]
    template_loader = jinja2.FileSystemLoader(searchpath="./")
    template_env = jinja2.Environment(loader=template_loader)
    template = template_env.get_template("graph.template")
    with open("{0}.dot".format(name), "w") as file:
        file.write(template.render(world=world, get_color=get_color))
        file.write("\n\n")
