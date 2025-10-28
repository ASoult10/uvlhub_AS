import os
import subprocess

import click


@click.command("selenium", help="Executes Selenium tests based on the environment.")
@click.argument("module", required=False)
def selenium(module):
    # Absolute paths
    working_dir = os.getenv("WORKING_DIR", "")
    modules_dir = os.path.join(working_dir, "app/modules")

    def validate_module(module):
        """Check if the module exists."""
        if module:
            module_path = os.path.join(modules_dir, module)
            if not os.path.exists(module_path):
                raise click.UsageError(f"Module '{module}' does not exist.")
            selenium_test_path = os.path.join(module_path, "tests", "test_selenium.py")
            if not os.path.exists(selenium_test_path):
                raise click.UsageError(
                    f"Selenium test for module '{module}' does not exist at path " f"'{selenium_test_path}'."
                )

    def run_selenium_tests_in_local(module):
        """Run the Selenium tests."""
        if module:
            module_name = f"app.modules.{module}.tests.test_selenium"
            test_command = ["python", "-m", module_name]
        else:
            module_names = []
            for mod in os.listdir(modules_dir):
                tests_dir = os.path.join(modules_dir, mod, "tests")
                selenium_test_path = os.path.join(tests_dir, "test_selenium.py")
                if os.path.exists(selenium_test_path):
                    module_names.append(f"app.modules.{mod}.tests.test_selenium")

            # ejecutamos todos los módulos uno tras otro
            for module_name in module_names:
                test_command = ["python", "-m", module_name]
                click.echo(f"Running Selenium tests with command: {' '.join(test_command)}")
                subprocess.run(test_command, check=True)
            return  # importante: no seguimos con el bloque común

        click.echo(f"Running Selenium tests with command: {' '.join(test_command)}")
        subprocess.run(test_command, check=True)

    # Validate module if provided
    if module:
        validate_module(module)

    if working_dir == "/app/":

        click.echo(
            click.style(
                "Currently it is not possible to run this "
                "command from a Docker environment, do you want to implement it yourself? ^^",
                fg="red",
            )
        )

    elif working_dir == "":
        run_selenium_tests_in_local(module)

    elif working_dir == "/vagrant/":

        click.echo(
            click.style(
                "Currently it is not possible to run this "
                "command from a Vagrant environment, do you want to implement it yourself? ^^",
                fg="red",
            )
        )

    else:
        click.echo(click.style(f"Unrecognized WORKING_DIR: {working_dir}", fg="red"))
