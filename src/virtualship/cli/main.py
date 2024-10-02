import click

from . import commands


@click.group()
def cli():
    pass


cli.add_command(commands.init)
cli.add_command(commands.fetch)
cli.add_command(commands.run)

if __name__ == "__main__":
    cli()