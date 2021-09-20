import click


def read_user_variable(var_name, default_value=None):
    return click.prompt(var_name, default=default_value)


def read_bool(prompt):
    return click.prompt(prompt, type=click.BOOL)


def read_choice():
    pass
